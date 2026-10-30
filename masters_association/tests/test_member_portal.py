"""Real document/workflow/identity tests. Run on a disposable Frappe test site."""

import base64
import hashlib
import re
from datetime import timedelta
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import frappe
from frappe.model.workflow import apply_workflow
from frappe.tests import IntegrationTestCase
from frappe.utils import now_datetime
from frappe.utils.password import check_password, update_password
from PIL import Image

from masters_association import member_portal as portal


class TestMemberPortal(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("member_portal_test")
		self.addCleanup(self._rollback)
		self.mail = self.enterContext(patch("frappe.sendmail"))
		# Do not execute or publish background work from rollback-only test data.
		self.enqueue = self.enterContext(patch("frappe.enqueue"))
		self.suffix = frappe.generate_hash(length=10)
		self.manager = self._user("manager", roles=["Masters Manager"])
		frappe.local.login_manager = SimpleNamespace(check_password=check_password)

	def _rollback(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="member_portal_test")

	def _user(self, prefix, roles=None):
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": f"portal-{prefix}-{self.suffix}@example.com",
				"first_name": prefix.title(),
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles or []],
			}
		).insert(ignore_permissions=True)

	def _member(self, prefix="Member", *, eligible=True, email=None):
		member = frappe.get_doc(
			{
				"doctype": portal.MEMBER,
				"name1": f"{prefix} {self.suffix}",
				"email": email or f"portal-{prefix.lower()}-{self.suffix}@example.com",
				"mobile_no_whatsapp": "+919876543210",
				"district": "Thrissur",
				"gst": f"TEST-{prefix}-{self.suffix}",
				"membership_status": "Normal Member",
				"portal_enabled": 1,
			}
		).insert(ignore_permissions=True)
		if eligible:
			# Fixture setup only; actual transition behavior is tested separately below.
			member.db_set("application_status", "Approved")
		return member

	def _provision(self, member):
		frappe.set_user(self.manager.name)
		result = portal.create_member_user(member.name)
		self.assertFalse(result.get("error"), result)
		member.reload()
		return member.user

	def test_approval_enqueues_only_after_commit_and_reapproval_is_idempotent(self):
		member = self._member(eligible=False)
		frappe.set_user(self.manager.name)
		apply_workflow(member.as_dict(), "Approve")
		jobs = [
			call
			for call in self.enqueue.call_args_list
			if call.args and call.args[0] == "masters_association.member_portal.provision_member_user"
		]
		self.assertEqual(len(jobs), 1)
		self.assertTrue(jobs[0].kwargs["enqueue_after_commit"])
		member.reload()
		user = self._provision(member)
		self.mail.reset_mock()
		self.assertEqual(portal.create_member_user(member.name)["user"], user)
		self.mail.assert_not_called()
		apply_workflow(member.as_dict(), "Review")
		member.reload()
		apply_workflow(member.as_dict(), "Approve")
		member.reload()
		self.assertEqual(member.user, user)

	def test_new_account_is_website_only_and_conflicts_require_explicit_link(self):
		member = self._member()
		user = self._provision(member)
		account = frappe.get_doc("User", user)
		self.assertEqual(account.user_type, "Website User")
		self.assertEqual({row.role for row in account.roles}, {portal.PORTAL_ROLE})
		self.assertEqual(account.first_name, member.name1)
		self.assertTrue(self.mail.called)
		other = self._member("Conflict", email=self.manager.name)
		result = portal.create_member_user(other.name)
		self.assertIn("System Manager", result["error"])
		other.reload()
		self.assertFalse(other.user)
		self.assertEqual(other.application_status, "Approved")
		self.assertTrue(other.account_setup_error)

	def test_missing_email_and_invitation_failure_are_retryable(self):
		member = self._member()
		member.email = ""
		member.save(ignore_permissions=True)
		frappe.set_user(self.manager.name)
		self.assertTrue(portal.create_member_user(member.name).get("error"))
		member.reload()
		self.assertFalse(member.user)
		member.email = f"retry-{self.suffix}@example.com"
		member.save()
		with patch(
			"frappe.core.doctype.user.user.User.send_welcome_mail_to_user",
			side_effect=frappe.OutgoingEmailError,
		):
			result = portal.create_member_user(member.name)
		self.assertTrue(result.get("user"))
		self.assertTrue(result.get("error"))
		member.reload()
		linked_user = member.user
		result = portal.send_member_invitation(member.name)
		self.assertEqual(result["user"], linked_user)
		self.assertFalse(frappe.db.get_value(portal.MEMBER, member.name, "account_setup_error"))

	def test_profile_api_exposes_only_own_allowlisted_fields_and_preserves_workflow(self):
		member = self._member()
		user = self._provision(member)
		other = self._member("Other")
		frappe.set_user(user)
		profile = portal.get_my_profile()
		self.assertEqual(profile["name"], member.name)
		self.assertNotIn("review_notes", profile)
		self.assertNotIn("company_bank_acc_no", profile)
		self.assertFalse(frappe.has_permission(portal.MEMBER, "read", doc=other))
		self.assertFalse(frappe.has_permission(portal.MEMBER, "write", doc=member))
		with self.assertRaises(frappe.PermissionError):
			frappe.get_list(portal.MEMBER)
		updated = portal.update_my_profile(
			{"name1": "Changed Member", "total_number_of_hybrid": "3"}, profile["modified"]
		)
		self.assertEqual(updated["name1"], "Changed Member")
		self.assertEqual(updated["total_number_of_hybrid"], 3)
		self.assertEqual(frappe.db.get_value(portal.MEMBER, member.name, "application_status"), "Approved")
		self.assertEqual(frappe.db.get_value("User", user, "first_name"), "Changed Member")
		for data in (
			{"application_status": "Approved"},
			{"user": self.manager.name},
			{"photo": "/files/another.png"},
			{"name": other.name},
		):
			with self.assertRaises(frappe.PermissionError):
				portal.update_my_profile(data, updated["modified"])
		with self.assertRaises(frappe.TimestampMismatchError):
			portal.update_my_profile({"designation": "Installer"}, profile["modified"])

	def test_profile_validation_and_revocation(self):
		member = self._member()
		user = self._provision(member)
		frappe.set_user(user)
		for invalid in (-1, "1.5", "²", True, "999999999999"):
			with self.assertRaises(frappe.ValidationError):
				portal.update_my_profile({"total_number_of_hybrid": invalid}, str(member.modified))
		with self.assertRaises(frappe.ValidationError):
			portal.update_my_profile({"google_maps_link": "https://127.0.0.1/secret"}, str(member.modified))
		for field, value in (
			("portal_enabled", 0),
			("application_status", "Pending"),
			("application_status", "Rejected"),
			("membership_status", "Not A Member"),
		):
			frappe.db.set_value(portal.MEMBER, member.name, field, value)
			with self.assertRaises(frappe.PermissionError):
				portal.get_my_profile()
			self.assertFalse(portal.get_session()["has_member_access"])
			frappe.db.set_value(
				portal.MEMBER,
				member.name,
				{"portal_enabled": 1, "application_status": "Approved", "membership_status": "Normal Member"},
			)

	def test_generic_user_writes_and_rename_do_not_bypass_profile_or_password_flow(self):
		member = self._member()
		user = self._provision(member)
		frappe.set_user(user)
		for field, value in (
			("first_name", "Bypass"),
			("user_image", "/files/other.png"),
			("new_password", "DirectPassword123!"),
		):
			account = frappe.get_doc("User", user)
			account.set(field, value)
			with self.assertRaises(frappe.PermissionError):
				account.save(ignore_permissions=True)
		with self.assertRaises(frappe.PermissionError):
			frappe.rename_doc("User", user, f"unverified-{self.suffix}@example.com")

	def test_photo_upload_removal_and_actual_format_validation(self):
		member = self._member()
		user = self._provision(member)
		frappe.set_user(user)
		buffer = BytesIO()
		Image.new("RGB", (8, 8), "green").save(buffer, format="PNG")
		photo = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
		profile = portal.upload_my_photo(photo, "untrusted.html", str(member.modified))
		self.assertTrue(profile["photo"].endswith(".png"))
		self.assertEqual(frappe.db.get_value("User", user, "user_image"), profile["photo"])
		attachment = frappe.db.get_value(
			"File",
			{"file_url": profile["photo"], "attached_to_doctype": portal.MEMBER},
			["attached_to_name", "attached_to_field"],
			as_dict=True,
		)
		self.assertEqual(attachment.attached_to_name, member.name)
		self.assertEqual(attachment.attached_to_field, "photo")
		profile = portal.remove_my_photo(profile["modified"])
		self.assertFalse(profile["photo"])
		self.assertFalse(frappe.db.get_value("User", user, "user_image"))
		with self.assertRaises(frappe.ValidationError):
			portal.upload_my_photo(
				base64.b64encode(b"<html>fake</html>").decode(), "fake.jpg", profile["modified"]
			)

	def test_existing_staff_link_preserves_roles_and_rejects_other_member(self):
		member = self._member()
		frappe.set_user(self.manager.name)
		with self.assertRaises(frappe.PermissionError):
			portal.link_member_user(member.name, self.manager.name)
		frappe.set_user("Administrator")
		self.assertEqual(
			portal.get_user_link_preview(member.name, self.manager.name)["user"]["user_type"], "System User"
		)
		portal.link_member_user(member.name, self.manager.name)
		account = frappe.get_doc("User", self.manager.name)
		self.assertIn("Masters Manager", [row.role for row in account.roles])
		self.assertIn(portal.PORTAL_ROLE, [row.role for row in account.roles])
		self.assertEqual(account.user_type, "System User")
		other = self._member("Other")
		with self.assertRaises(frappe.ValidationError):
			portal.link_member_user(other.name, self.manager.name)

	def test_existing_role_profiles_keep_their_roles_and_gain_member_profile(self):
		profile = frappe.get_doc(
			{
				"doctype": "Role Profile",
				"role_profile": f"Managers {self.suffix}",
				"roles": [{"role": "Masters Manager"}],
			}
		).insert(ignore_permissions=True)
		account = frappe.get_doc("User", self.manager.name)
		account.append("role_profiles", {"role_profile": profile.name})
		account.save(ignore_permissions=True)
		member = self._member()
		portal.link_member_user(member.name, account.name)
		account.reload()
		self.assertEqual(
			{row.role_profile for row in account.role_profiles}, {profile.name, "Masters Member Portal"}
		)
		self.assertTrue({"Masters Manager", portal.PORTAL_ROLE}.issubset({row.role for row in account.roles}))

	def _request_email(self, member, new_email=None):
		update_password(member.user, "CurrentPassword123!")
		frappe.set_user(member.user)
		new_email = new_email or f"changed-{self.suffix}@example.com"
		portal.request_email_change(new_email, "CurrentPassword123!")
		message = self.mail.call_args.kwargs["message"]
		link = re.search(r'href="([^"]+)"', message)[1]
		return parse_qs(urlparse(link).query)["email_token"][0], new_email

	def test_verified_email_renames_user_updates_link_and_is_single_use(self):
		member = self._member()
		old_user = self._provision(member)
		token, new_email = self._request_email(member)
		request = frappe.get_doc(portal.EMAIL_REQUEST, {"user": old_user})
		self.assertNotEqual(request.token_hash, token)
		self.assertEqual(request.token_hash, hashlib.sha256(token.encode()).hexdigest())
		result = portal.confirm_email_change(token)
		self.assertTrue(result["login_required"])
		member.reload()
		self.assertEqual((member.user, member.email), (new_email, new_email))
		self.assertFalse(frappe.db.exists("User", old_user))
		self.assertTrue(frappe.db.exists("User", new_email))
		self.assertTrue(check_password(new_email, "CurrentPassword123!"))
		frappe.set_user(new_email)
		with self.assertRaises(frappe.ValidationError):
			portal.confirm_email_change(token)

	def test_email_expiry_replacement_collision_and_wrong_user(self):
		member = self._member()
		self._provision(member)
		token, new_email = self._request_email(member)
		request_name = frappe.db.get_value(portal.EMAIL_REQUEST, {"user": member.user}, "name")
		frappe.db.set_value(
			portal.EMAIL_REQUEST, request_name, "expires_at", now_datetime() - timedelta(seconds=1)
		)
		with self.assertRaises(frappe.ValidationError):
			portal.confirm_email_change(token)
		new_token, _ = self._request_email(member, new_email)
		with self.assertRaises(frappe.ValidationError):
			portal.confirm_email_change(token)
		frappe.set_user("Administrator")
		other = self._member("Other")
		other_user = self._provision(other)
		frappe.set_user(other_user)
		with self.assertRaises(frappe.ValidationError):
			portal.confirm_email_change(new_token)
		frappe.set_user("Administrator")
		frappe.get_doc(
			{"doctype": "User", "email": new_email, "first_name": "Collision", "send_welcome_email": 0}
		).insert(ignore_permissions=True)
		frappe.set_user(member.user)
		with self.assertRaises(frappe.ValidationError):
			portal.confirm_email_change(new_token)
		member.reload()
		self.assertNotEqual(member.email, new_email)

	def test_email_change_with_active_sessions_rolls_back_if_password_rename_fails(self):
		member = self._member()
		old_user = self._provision(member)
		token, new_email = self._request_email(member)
		session_id = "member-rename-test-" + self.suffix
		frappe.db.sql(
			"INSERT INTO `tabSessions` (`user`, `sid`, `sessiondata`, `lastupdate`) VALUES (%s, %s, %s, %s)",
			(old_user, session_id, "{}", now_datetime()),
		)
		frappe.db.savepoint("before_failed_email_rename")
		with patch(
			"frappe.model.rename_doc.rename_password",
			side_effect=frappe.ValidationError("Forced rename failure"),
		):
			with self.assertRaises(frappe.ValidationError):
				portal.confirm_email_change(token)
		# This savepoint would be gone if native session invalidation committed.
		frappe.db.rollback(save_point="before_failed_email_rename")
		member.reload()
		self.assertEqual((member.user, member.email), (old_user, old_user))
		self.assertTrue(frappe.db.exists("User", old_user))
		self.assertFalse(frappe.db.exists("User", new_email))
		self.assertFalse(frappe.db.get_value(portal.EMAIL_REQUEST, {"user": old_user}, "used"))
		self.assertTrue(check_password(old_user, "CurrentPassword123!"))
		self.assertTrue(frappe.db.sql("SELECT sid FROM `tabSessions` WHERE sid = %s", session_id))
		portal.confirm_email_change(token)
		self.assertEqual(frappe.db.get_value(portal.MEMBER, member.name, "email"), new_email)
		self.assertFalse(frappe.db.sql("SELECT sid FROM `tabSessions` WHERE sid = %s", session_id))

	def test_administrative_rename_also_updates_member_and_manager_has_no_external_business_read(self):
		member = self._member()
		old_user = self._provision(member)
		frappe.set_user("Administrator")
		new_email = f"admin-renamed-{self.suffix}@example.com"
		frappe.rename_doc("User", old_user, new_email, show_alert=False)
		member.reload()
		self.assertEqual((member.user, member.email), (new_email, new_email))
		frappe.set_user(self.manager.name)
		if frappe.db.exists("DocType", "Quality Goal"):
			doc = frappe.get_doc(
				{"doctype": "Quality Goal", "name": "Test Quality Goal", "owner": self.manager.name}
			)
			self.assertFalse(frappe.has_permission("Quality Goal", "read", doc=doc))
			self.assertEqual(frappe.get_list("Quality Goal"), [])
		for doctype in (
			"Association Member",
			"Website Enquiry",
			"Gallery Item",
			"Association Event",
			"Association Document",
		):
			self.assertTrue(frappe.has_permission(doctype, "create"))
		self.assertFalse(frappe.has_permission("User", "create"))
