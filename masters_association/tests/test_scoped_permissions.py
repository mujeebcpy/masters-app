"""Policy and metadata tests which do not require a running Frappe site."""

import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

APP_ROOT = Path(__file__).resolve().parents[1]


class AttrDict(dict):
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__


def load_permissions():
	frappe_stub = types.ModuleType("frappe")
	spec = importlib.util.spec_from_file_location(
		"_masters_scoped_permissions_test", APP_ROOT / "permissions.py"
	)
	module = importlib.util.module_from_spec(spec)
	with patch.dict(sys.modules, {"frappe": frappe_stub}):
		spec.loader.exec_module(module)
	return module, frappe_stub


class TestScopedPermissions(unittest.TestCase):
	def setUp(self):
		self.permissions, self.frappe = load_permissions()
		self.roles = {"Masters Manager", "All", "Guest", "Desk User"}
		self.rows = []
		self.frappe.get_roles = Mock(side_effect=lambda user: list(self.roles))
		self.frappe.get_meta = Mock(side_effect=lambda doctype: AttrDict(permissions=self.rows))
		self.frappe.get_doctype_app = Mock(
			side_effect=lambda doctype: "masters_association"
			if doctype.startswith("Association ")
			else "erpnext"
		)
		self.frappe.session = AttrDict(user="member@example.com")
		self.frappe.db = AttrDict(escape=lambda value: "'" + value.replace("'", "''") + "'")
		self.doc = AttrDict(doctype="Quality Goal", name="QG-001", owner="someone@example.com")

	def row(self, role, **rights):
		row = AttrDict(role=role, permlevel=0, **rights)
		self.rows.append(row)
		return row

	def allowed(self, ptype="read"):
		return self.permissions.has_scoped_permission(self.doc, ptype=ptype)

	def query(self):
		return self.permissions.get_scoped_query_conditions(doctype=self.doc.doctype)

	def test_desk_user_baseline_does_not_expose_quality_records(self):
		self.row("Desk User", read=1, report=1, print=1)
		self.assertFalse(self.allowed())
		self.assertFalse(self.allowed("print"))
		self.assertEqual(self.query(), "1=0")

	def test_all_role_does_not_expose_business_settings_to_portal_user(self):
		self.roles = {"Association Member", "All", "Guest"}
		self.doc.doctype = "Voice Call Settings"
		self.row("All", read=1, create=1, write=1, delete=1)
		for operation in ("read", "create", "write", "delete"):
			self.assertFalse(self.allowed(operation))
		self.assertEqual(self.query(), "1=0")

	def test_unrelated_additional_role_does_not_lift_restrictions(self):
		self.roles.add("Sales User")
		self.row("Desk User", read=1)
		self.row("Quality Manager", read=1, write=1)
		self.assertFalse(self.allowed())
		self.assertEqual(self.query(), "1=0")

	def test_explicit_role_grants_only_its_operations(self):
		self.roles.add("Quality Reader")
		self.row("Desk User", read=1, write=1)
		self.row("Quality Reader", read=1)
		self.assertTrue(self.allowed())
		self.assertTrue(self.allowed("select"))
		self.assertFalse(self.allowed("write"))
		self.assertFalse(self.allowed("create"))
		self.assertEqual(self.query(), "")

	def test_higher_permission_level_is_not_a_record_grant(self):
		self.roles.add("Quality Reader")
		self.row("Quality Reader", read=1).permlevel = 1
		self.assertFalse(self.allowed())
		self.assertEqual(self.query(), "1=0")

	def test_effective_custom_permissions_are_used(self):
		self.roles.add("Quality Reader")
		# The effective metadata has no read grant, even if a standard DocPerm had one.
		self.row("Quality Reader", read=0, write=0)
		self.assertFalse(self.allowed())
		self.assertEqual(self.query(), "1=0")

	def test_explicit_owner_grant_stays_owner_restricted_despite_baseline(self):
		self.roles.add("Quality Reader")
		self.row("Desk User", read=1)
		self.row("Quality Reader", read=1, if_owner=1)
		self.assertFalse(self.allowed())
		self.doc.owner = self.frappe.session.user
		self.assertTrue(self.allowed())
		self.assertEqual(self.query(), "`tabQuality Goal`.`owner` = 'member@example.com'")

	def test_query_escapes_user_and_table_identifiers(self):
		self.roles.add("Quality Reader")
		self.row("Quality Reader", read=1, if_owner=1)
		self.doc.doctype = "Custom`Records"
		self.frappe.session.user = "o'connor@example.com"
		self.assertEqual(self.query(), "`tabCustom``Records`.`owner` = 'o''connor@example.com'")

	def test_explicit_select_only_grant_does_not_grant_document_read(self):
		self.roles.add("Stock User")
		self.row("Stock User", select=1)
		self.assertTrue(self.allowed("select"))
		self.assertFalse(self.allowed())
		self.assertEqual(self.query(), "")

	def test_automatic_read_cannot_promote_explicit_select_to_full_list_access(self):
		self.roles.add("Stock User")
		self.row("Desk User", read=1)
		self.row("Stock User", select=1)
		self.assertTrue(self.allowed("select"))
		self.assertFalse(self.allowed())
		self.assertEqual(self.query(), "1=0")

	def test_unrestricted_users_keep_framework_permissions(self):
		for roles, user in (
			({"Masters Manager", "System Manager"}, "admin@example.com"),
			({"Masters Manager"}, "Administrator"),
			({"Sales User", "Desk User", "All"}, "staff@example.com"),
			({"Guest"}, "Guest"),
		):
			with self.subTest(roles=roles, user=user):
				self.roles = roles
				self.assertTrue(self.permissions.has_scoped_permission(self.doc, user=user))
				self.assertEqual(
					self.permissions.get_scoped_query_conditions(user=user, doctype=self.doc.doctype), ""
				)

	def test_core_services_and_masters_keep_underlying_permission_checks(self):
		for doctype in ("User", "File", "DocType", "Workspace", "Workflow State", "Association Member"):
			with self.subTest(doctype=doctype):
				self.doc.doctype = doctype
				self.assertTrue(self.allowed())
				self.assertEqual(self.query(), "")
		self.frappe.get_meta.assert_not_called()

	def test_other_framework_features_are_not_blanket_exempt(self):
		self.doc.doctype = "Connected App"
		self.frappe.get_doctype_app.return_value = "frappe"
		self.frappe.get_doctype_app.side_effect = None
		self.row("All", read=1)
		self.assertFalse(self.allowed())


class TestMastersRoleMetadata(unittest.TestCase):
	def load(self, relative):
		return json.loads((APP_ROOT / relative).read_text())

	def test_management_and_portal_roles_have_separate_desk_access(self):
		roles = {row["name"]: row for row in self.load("fixtures/role.json")}
		self.assertEqual(roles["Masters Manager"]["desk_access"], 1)
		self.assertEqual(roles["Association Member"]["desk_access"], 0)
		self.assertNotIn("Membership Reviewer", roles)

	def test_every_parent_doctype_has_manager_permissions_and_no_portal_crud(self):
		business_doctypes = {
			"Association Member",
			"Website Enquiry",
			"Gallery Item",
			"Association Event",
			"Association Document",
		}
		parents = []
		for path in (APP_ROOT / "masters_association/doctype").glob("*/*.json"):
			doc = json.loads(path.read_text())
			if doc["name"] not in business_doctypes:
				continue
			parents.append(doc["name"])
			manager = [
				row
				for row in doc["permissions"]
				if row["role"] == "Masters Manager" and not row.get("permlevel")
			]
			self.assertEqual(len(manager), 1, doc["name"])
			for operation in ("read", "write", "create", "delete"):
				self.assertEqual(manager[0].get(operation), 1, (doc["name"], operation))
			self.assertFalse(manager[0].get("share"), doc["name"])
			self.assertFalse(
				any(
					row["role"] in {"Association Member", "Membership Reviewer"} for row in doc["permissions"]
				)
			)
		self.assertEqual(len(parents), 5)

	def test_portal_role_profile_preserves_profile_based_user_roles(self):
		profile = self.load("fixtures/role_profile.json")[0]
		self.assertEqual(profile["name"], "Masters Member Portal")
		self.assertEqual(profile["roles"], [{"role": "Association Member"}])

	def test_member_link_and_portal_controls_are_internal(self):
		doc = self.load("masters_association/doctype/association_member/association_member.json")
		fields = {row["fieldname"]: row for row in doc["fields"]}
		self.assertEqual(fields["user"]["options"], "User")
		for flag in ("unique", "read_only", "no_copy"):
			self.assertEqual(fields["user"][flag], 1)
		for fieldname in ("user", "portal_enabled", "account_setup_error"):
			self.assertEqual(fields[fieldname]["permlevel"], 1)
			self.assertIn(fieldname, doc["field_order"])
		self.assertEqual(fields["portal_enabled"]["default"], "1")
		self.assertEqual(doc["track_changes"], 1)

	def test_workflow_uses_manager_without_self_approval(self):
		workflow = self.load("fixtures/workflow.json")[0]
		self.assertEqual({row["allow_edit"] for row in workflow["states"]}, {"Masters Manager"})
		self.assertEqual({row["allowed"] for row in workflow["transitions"]}, {"Masters Manager"})
		self.assertTrue(all(row["allow_self_approval"] == 0 for row in workflow["transitions"]))

	def test_navigation_does_not_expose_global_website_administration(self):
		workspace = self.load("masters_association/workspace/masters/masters.json")
		sidebar = self.load("masters_association/sidebar/masters/masters.json")
		for row in workspace["links"] + sidebar["items"]:
			self.assertNotIn(row.get("link_to"), {"Web Form", "Website Settings", "Website Script"})
		for navigation in (workspace, self.load("desktop_icon/masters.json")):
			self.assertEqual(
				{row["role"] for row in navigation["roles"]}, {"Masters Manager", "System Manager"}
			)


if __name__ == "__main__":
	unittest.main()
