"""Real File-controller regression tests; run on a disposable Frappe site."""

import base64
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase
from PIL import Image

from masters_association import member_portal as portal


class TestMemberFiles(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("member_file_test")
		self.addCleanup(self._rollback)
		self.enterContext(patch("frappe.sendmail"))
		self.enterContext(patch("frappe.enqueue"))
		self.suffix = frappe.generate_hash(length=10)
		self.member = frappe.get_doc(
			{
				"doctype": portal.MEMBER,
				"name1": f"File Member {self.suffix}",
				"email": f"file-member-{self.suffix}@example.com",
				"mobile_no_whatsapp": "+919876543210",
				"district": "Thrissur",
				"gst": f"TEST-FILE-{self.suffix}",
				"membership_status": "Normal Member",
				"portal_enabled": 1,
			}
		).insert(ignore_permissions=True)
		self.member.db_set("application_status", "Approved")
		result = portal.create_member_user(self.member.name)
		self.assertFalse(result.get("error"), result)
		self.member.reload()
		self.user = self.member.user
		frappe.set_user(self.user)
		buffer = BytesIO()
		image = Image.new("RGB", (8, 8), "green")
		image.putpixel((0, 0), tuple(self.suffix.encode()[:3]))
		image.save(buffer, format="PNG")
		image.close()
		photo = "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()
		self.profile = portal.upload_my_photo(photo, "portrait.png", str(self.member.modified))
		self.photo_url = self.profile["photo"]
		self.portrait = frappe.get_doc(
			"File",
			{
				"file_url": self.photo_url,
				"attached_to_doctype": portal.MEMBER,
				"attached_to_name": self.member.name,
				"attached_to_field": "photo",
			},
		)
		self.avatar = frappe.get_doc(
			"File",
			{
				"file_url": self.photo_url,
				"attached_to_doctype": "User",
				"attached_to_name": self.user,
				"attached_to_field": "user_image",
			},
		)
		self.photo_path = Path(self.portrait.get_full_path())
		self.original_bytes = self.photo_path.read_bytes()

	def _rollback(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="member_file_test")

	def assert_portrait_intact(self):
		self.assertEqual(frappe.db.get_value(portal.MEMBER, self.member.name, "photo"), self.photo_url)
		self.assertEqual(frappe.db.get_value("User", self.user, "user_image"), self.photo_url)
		self.assertTrue(self.photo_path.exists())
		self.assertEqual(self.photo_path.read_bytes(), self.original_bytes)

	def test_avatar_privacy_change_cannot_move_shared_portrait(self):
		self.avatar.is_private = 1
		with self.assertRaises(frappe.PermissionError):
			self.avatar.save()
		self.assertEqual(frappe.db.get_value("File", self.avatar.name, "file_url"), self.photo_url)
		self.assert_portrait_intact()

	def test_photo_file_url_or_reparent_cannot_detach_a_protected_reference(self):
		for changes in (
			{"file_url": "https://example.com/another-image.png"},
			{"attached_to_doctype": None, "attached_to_name": None, "attached_to_field": None},
			{
				"file_url": "https://example.com/another-image.png",
				"attached_to_doctype": None,
				"attached_to_name": None,
				"attached_to_field": None,
			},
		):
			with self.subTest(changes=changes):
				file = frappe.get_doc("File", self.portrait.name)
				file.update(changes)
				with self.assertRaises(frappe.PermissionError):
					file.save()
				self.assert_portrait_intact()

	def test_delete_is_blocked_before_native_file_controller_touches_disk(self):
		for user in (self.user, "Administrator"):
			with self.subTest(user=user):
				frappe.set_user(user)
				with self.assertRaises(frappe.PermissionError):
					frappe.delete_doc("File", self.portrait.name)
				self.assertTrue(frappe.db.exists("File", self.portrait.name))
				self.assert_portrait_intact()

	def test_new_alias_cannot_later_move_a_shared_portrait(self):
		alias = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "portrait-alias.png",
				"file_url": self.photo_url,
				"is_private": 0,
			}
		).insert()
		alias.is_private = 1
		with self.assertRaises(frappe.PermissionError):
			alias.save()
		self.assert_portrait_intact()

	def test_arbitrary_linked_user_field_attachment_is_rejected(self):
		for fieldname in ("user_image", "first_name"):
			with self.subTest(fieldname=fieldname):
				with self.assertRaises(frappe.PermissionError):
					frappe.get_doc(
						{
							"doctype": "File",
							"file_name": f"new-{self.suffix}.txt",
							"content": b"unrelated pixels",
							"attached_to_doctype": "User",
							"attached_to_name": self.user,
							"attached_to_field": fieldname,
							"is_private": 0,
						}
					).insert()
		self.assert_portrait_intact()

	def test_native_optimize_cannot_overwrite_pixels_before_save_validation(self):
		with patch("frappe.utils.image.optimize_image", return_value=b"would overwrite the portrait"):
			with self.assertRaises(frappe.PermissionError):
				self.avatar.optimize_file()
		self.assert_portrait_intact()

	def test_forged_new_document_marker_cannot_bypass_native_optimize_guard(self):
		self.avatar.set("__islocal", True)
		with patch("frappe.utils.image.optimize_image", return_value=b"would overwrite the portrait"):
			with self.assertRaises(frappe.PermissionError):
				self.avatar.optimize_file()
		self.assert_portrait_intact()

	def test_forged_file_identity_cannot_hide_the_persisted_portrait_reference(self):
		forged = frappe.get_doc(
			{
				"doctype": "File",
				"name": self.avatar.name,
				"__islocal": True,
				"file_name": f"forged-{self.suffix}.txt",
				"file_url": "https://example.com/unrelated.txt",
				"content_hash": "unrelated-content-hash",
				"attached_to_doctype": None,
				"attached_to_name": None,
				"attached_to_field": None,
			}
		)
		self.assertIsNone(forged.get_doc_before_save())
		# Exercise the pre-write extension directly: it must reject before the
		# native save_file implementation can act on any forged attributes.
		with self.assertRaises(frappe.PermissionError):
			forged.save_file(content=b"would overwrite a blob", overwrite=True)
		self.assert_portrait_intact()

	def test_portal_removal_clears_both_profiles_and_unprotects_old_asset(self):
		profile = portal.remove_my_photo(self.profile["modified"])
		self.assertFalse(profile["photo"])
		self.assertFalse(frappe.db.get_value("User", self.user, "user_image"))
		frappe.delete_doc("File", self.portrait.name)
		self.assertFalse(frappe.db.exists("File", self.portrait.name))

	def test_unrelated_upload_and_delete_keep_normal_framework_behavior(self):
		file = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": f"unrelated-{self.suffix}.txt",
				"content": f"Unrelated member upload {self.suffix}".encode(),
				"is_private": 0,
			}
		).insert()
		file.file_name = f"renamed-{self.suffix}.txt"
		file.save()
		frappe.delete_doc("File", file.name)
		self.assertFalse(frappe.db.exists("File", file.name))
		self.assert_portrait_intact()
