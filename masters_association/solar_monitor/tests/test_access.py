"""Ownership and role boundaries for Solar Monitor. Run on a disposable Frappe test site."""

import json
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from masters_association import member_portal as portal
from masters_association.solar_monitor import access, api, service

SECRET = "super-secret-value"


class TestSolarAccess(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		frappe.db.savepoint("solar_access_test")
		self.addCleanup(self._rollback)
		self.enqueue = self.enterContext(patch("frappe.enqueue"))
		self.suffix = frappe.generate_hash(length=10)
		self.user_a, self.member_a = self._member("Alpha")
		self.user_b, self.member_b = self._member("Beta")
		self.viewer = self._user("viewer", [access.VIEWER_ROLE])
		self.admin = self._user("sysmgr", ["System Manager"])
		self.account_a = self._account(self.user_a, "Home")
		self.account_b = self._account(self.user_b, "Home")
		frappe.set_user("Administrator")
		self.station_a = self._station(self.account_a, "A")
		self.station_b = self._station(self.account_b, "B")

	def _rollback(self):
		frappe.set_user("Administrator")
		frappe.db.rollback(save_point="solar_access_test")

	def _user(self, prefix, roles):
		return frappe.get_doc(
			{
				"doctype": "User",
				"email": f"solar-{prefix}-{self.suffix}@example.com",
				"first_name": prefix.title(),
				"enabled": 1,
				"send_welcome_email": 0,
				"roles": [{"role": role} for role in roles],
			}
		).insert(ignore_permissions=True).name

	def _member(self, prefix):
		user = self._user(prefix.lower(), [portal.PORTAL_ROLE])
		member = frappe.get_doc(
			{
				"doctype": portal.MEMBER,
				"name1": f"{prefix} {self.suffix}",
				"email": user,
				"mobile_no_whatsapp": "+919876543210",
				"district": "Thrissur",
				"gst": f"SOLAR-{prefix}-{self.suffix}",
				"membership_status": "Normal Member",
				"portal_enabled": 1,
			}
		).insert(ignore_permissions=True)
		member.db_set({"application_status": "Approved", "user": user})
		return user, member.name

	def _account(self, user, label):
		frappe.set_user(user)
		data = {
			"account_label": label,
			"provider": "Deye",
			"region": "India",
			"app_id": "app",
			"app_secret": SECRET,
			"email": "owner@example.com",
			"password": SECRET,
			"company_id": "123",
		}
		return api.save_my_account(json.dumps(data))["name"]

	def _station(self, account, suffix):
		return frappe.get_doc(
			{
				"doctype": "Solar Station",
				"account": account,
				"external_id": f"ext-{suffix}-{self.suffix}",
				"station_name": f"Plant {suffix} {self.suffix}",
				"present": 1,
			}
		).insert(ignore_permissions=True).name

	def test_member_sees_only_own_graph(self):
		frappe.set_user(self.user_a)
		overview = api.get_overview()
		self.assertEqual(overview["scope"], "own")
		self.assertEqual({x.name for x in overview["accounts"]}, {self.account_a})
		self.assertEqual({x.name for x in overview["stations"]}, {self.station_a})
		self.assertEqual(overview["manageable_accounts"], [self.account_a])
		# A client-submitted member filter never widens a member's scope.
		self.assertEqual(
			{x.name for x in api.get_overview(member=self.member_b)["accounts"]}, {self.account_a}
		)
		with self.assertRaises(frappe.PermissionError):
			api.get_station(self.station_b)
		with self.assertRaises(frappe.ValidationError):
			api.get_overview(account=self.account_b)
		for call in (
			lambda: api.refresh_station(self.station_b),
			lambda: api.sync_inventory(self.account_b),
			lambda: api.test_connection(self.account_b),
			lambda: api.disable_my_account(self.account_b),
			lambda: api.enable_my_account(self.account_b),
			lambda: api.save_my_account(json.dumps({"account_label": "Mine"}), self.account_b),
		):
			with self.assertRaises(frappe.PermissionError):
				call()
		with self.assertRaises(frappe.ValidationError):
			api.check_alerts(self.account_b)

	def test_member_can_reenable_own_account(self):
		frappe.set_user(self.user_a)
		api.disable_my_account(self.account_a)
		self.assertEqual(frappe.db.get_value(service.ACCOUNT, self.account_a, "enabled"), 0)
		self.assertEqual(api.enable_my_account(self.account_a)["status"], "Enabled")
		self.assertEqual(frappe.db.get_value(service.ACCOUNT, self.account_a, "enabled"), 1)

	def test_station_inherits_owner(self):
		self.assertEqual(frappe.db.get_value("Solar Station", self.station_a, "member"), self.member_a)

	def test_members_have_no_document_permissions(self):
		frappe.set_user(self.user_a)
		for doctype in ("Solar API Account", "Solar Station", "Solar Device", "Solar Alert"):
			self.assertFalse(frappe.has_permission(doctype, "read"))
			with self.assertRaises(frappe.PermissionError):
				frappe.get_list(doctype)

	def test_global_roles_read_all_but_cannot_write(self):
		for user in (self.viewer, self.admin, "Administrator"):
			frappe.set_user(user)
			overview = api.get_overview()
			self.assertEqual(overview["scope"], "all")
			names = {x.name for x in overview["accounts"]}
			self.assertTrue({self.account_a, self.account_b} <= names)
			self.assertEqual(overview["manageable_accounts"], [])
			filtered = api.get_overview(member=self.member_b)
			self.assertEqual({x.name for x in filtered["accounts"]}, {self.account_b})
			self.assertFalse(api.get_station(self.station_a)["can_manage"])
			for call in (
				lambda: api.refresh_station(self.station_a),
				lambda: api.sync_inventory(self.account_a),
				lambda: api.test_connection(self.account_a),
				lambda: api.refresh_production(),
				lambda: api.check_alerts(),
				lambda: api.save_my_account(json.dumps({"account_label": "X"})),
				lambda: api.get_my_accounts(),
			):
				with self.assertRaises(frappe.PermissionError):
					call()
		frappe.set_user(self.viewer)
		self.assertTrue(frappe.has_permission("Solar Station", "read"))
		self.assertFalse(frappe.has_permission("Solar Station", "write"))
		self.assertFalse(frappe.has_permission("Solar API Account", "create"))

	def test_only_administrator_can_delete_solar_records(self):
		doctypes = ("Solar API Account", "Solar Station", "Solar Device", "Solar Alert", "Solar Monitor Settings")
		for user in (self.admin, self.viewer, self.user_a, self.user_b, "Guest"):
			frappe.set_user(user)
			for doctype in doctypes:
				self.assertFalse(frappe.has_permission(doctype, "delete"), doctype)
		frappe.set_user("Administrator")
		# Desk builds its delete actions from DocPerm, not has_permission's
		# special-case bypass for Administrator.
		from frappe.utils.user import UserPermissions

		permissions = UserPermissions("Administrator")
		permissions.build_permissions()
		for doctype in doctypes:
			self.assertTrue(frappe.has_permission(doctype, "delete"), doctype)
			self.assertIn(doctype, permissions.can_delete)
			self.assertEqual(
				{row.role for row in frappe.get_meta(doctype).permissions if row.get("delete")},
				{"Administrator"},
			)

	def test_secrets_are_never_returned(self):
		frappe.set_user(self.user_a)
		payloads = [api.get_my_accounts(), api.get_overview()]
		frappe.set_user(self.viewer)
		payloads.append(api.get_overview())
		for payload in payloads:
			self.assertNotIn(SECRET, frappe.as_json(payload))
		frappe.set_user(self.user_a)
		row = api.get_my_accounts()[0]
		self.assertTrue(row["has_app_secret"])
		self.assertFalse(row["has_client_secret"])
		# A blank secret keeps the stored value.
		api.save_my_account(json.dumps({"app_secret": ""}), self.account_a)
		self.assertEqual(
			frappe.get_doc(service.ACCOUNT, self.account_a).get_password("app_secret"), SECRET
		)

	def test_protected_fields_and_ownership(self):
		frappe.set_user(self.user_a)
		for data in ({"member": self.member_b}, {"access_token": "x"}, {"connection_status": "Connected"}):
			with self.assertRaises(frappe.ValidationError):
				api.save_my_account(json.dumps(data), self.account_a)
		frappe.set_user("Administrator")
		doc = frappe.get_doc(service.ACCOUNT, self.account_a)
		doc.member = self.member_b
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_labels_unique_per_member(self):
		# Both members already use "Home"; a second "Home" for the same member is rejected.
		with self.assertRaises(frappe.ValidationError):
			self._account(self.user_a, "Home")

	def test_revoked_member_stops_provider_calls_and_access(self):
		frappe.db.set_value(portal.MEMBER, self.member_a, "portal_enabled", 0)
		with self.assertRaises(service.ProviderError):
			service.account_doc(self.account_a)
		frappe.set_user(self.user_a)
		with self.assertRaises(frappe.PermissionError):
			api.get_overview()
		self.assertIsNone(access.session_access())

	def test_enphase_state_bound_to_user(self):
		frappe.cache().set_value(
			"solar-monitor-enphase-state:abc",
			{"account": self.account_a, "user": self.user_a, "member": self.member_a},
		)
		frappe.set_user(self.user_b)
		with self.assertRaises(frappe.ValidationError):
			api.enphase_callback(code="x", state="abc")
		frappe.set_user(self.user_a)
		# The state is one-use, so even the owner cannot replay it after the failed attempt.
		with self.assertRaises(frappe.ValidationError):
			api.enphase_callback(code="x", state="abc")

	def test_session_access(self):
		frappe.set_user(self.user_a)
		self.assertEqual(portal.get_session()["solar_access"], "own")
		frappe.set_user(self.viewer)
		self.assertEqual(portal.get_session()["solar_access"], "all")
		frappe.set_user("Guest")
		self.assertIsNone(portal.get_session()["solar_access"])
