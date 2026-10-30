"""Run without a site: python -m unittest discover -s masters_association/patches -p 'test_migrate_masters_manager.py'."""

import copy
import importlib.util
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


class FakeDatabase:
	def __init__(self):
		self.tables = {}

	def matches(self, row, filters):
		for field, value in (filters or {}).items():
			if isinstance(value, tuple):
				if value[0] != "in" or row.get(field) not in value[1]:
					return False
			elif row.get(field) != value:
				return False
		return True

	def rows(self, doctype, filters=None):
		if isinstance(filters, str):
			filters = {"name": filters}
		return [row for row in self.tables.get(doctype, []) if self.matches(row, filters)]

	def exists(self, doctype, filters):
		rows = self.rows(doctype, filters)
		return rows[0]["name"] if rows else None

	def get_value(self, doctype, filters, field):
		rows = self.rows(doctype, filters)
		return rows[0].get(field) if rows else None

	def set_value(self, doctype, name, field, value, **_kwargs):
		self.rows(doctype, name)[0][field] = value

	def delete(self, doctype, filters):
		self.tables[doctype] = [row for row in self.tables.get(doctype, []) if not self.matches(row, filters)]


class FakeDocument(SimpleNamespace):
	def insert(self, **_kwargs):
		frappe = self._frappe
		rows = frappe.db.tables.setdefault(self.doctype, [])
		self.name = getattr(self, "name", None) or (
			self.role_name if self.doctype == "Role" else f"{self.doctype}-{len(rows) + 1}"
		)
		rows.append(self.values())
		return self

	def save(self, **_kwargs):
		self._frappe.saved_doctypes.append(self.doctype)
		self._frappe.db.rows(self.doctype, self.name)[0].update(self.values())
		return self

	def values(self):
		return {key: value for key, value in vars(self).items() if key != "_frappe"}


class TestMigrateMastersManager(unittest.TestCase):
	def setUp(self):
		self.frappe = ModuleType("frappe")
		self.frappe.db = FakeDatabase()
		self.frappe.clear_cache = Mock()
		self.frappe.clear_document_cache = Mock()
		self.frappe.saved_doctypes = []
		self.frappe.LinkExistsError = type("LinkExistsError", (Exception,), {})
		self.frappe.get_all = self.get_all
		self.frappe.get_doc = self.get_doc
		self.frappe.get_meta = lambda doctype: SimpleNamespace(
			get_field=lambda field: field if field in self.meta_fields.get(doctype, set()) else None
		)
		self.meta_fields = {"Workspace": {"module"}, "Desktop Icon": {"app"}}
		self.dynamic_links = []
		delete_module = ModuleType("frappe.model.delete_doc")
		delete_module.get_linked_docs = lambda _role: self.role_links()
		delete_module.get_dynamic_linked_docs = lambda _role: self.dynamic_links
		delete_module.check_if_doc_is_linked = lambda _role: self.assert_no_links(self.role_links())
		delete_module.check_if_doc_is_dynamically_linked = lambda _role: self.assert_no_links(
			self.dynamic_links
		)
		self.modules = patch.dict(
			"sys.modules", {"frappe": self.frappe, "frappe.model.delete_doc": delete_module}
		)
		self.modules.start()
		self.addCleanup(self.modules.stop)
		path = Path(__file__).with_name("migrate_masters_manager.py")
		spec = importlib.util.spec_from_file_location("masters_manager_migration_unit", path)
		self.migration = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(self.migration)
		self.add(
			"Role", name="Membership Reviewer", role_name="Membership Reviewer", disabled=0, desk_access=1
		)

	def add(self, doctype, **values):
		values.setdefault("name", f"{doctype}-{len(self.frappe.db.tables.get(doctype, [])) + 1}")
		self.frappe.db.tables.setdefault(doctype, []).append(values)
		return values

	def add_role(self, user, role, *, parenttype="User"):
		return self.add("Has Role", parent=user, parenttype=parenttype, parentfield="roles", role=role, idx=1)

	def roles(self, name, parenttype="User"):
		return self.get_all("Has Role", filters={"parent": name, "parenttype": parenttype}, pluck="role")

	def get_all(self, doctype, *, filters=None, fields=None, pluck=None):
		rows = self.frappe.db.rows(doctype, filters)
		if pluck:
			return [row.get(pluck) for row in rows]
		return [SimpleNamespace(**{field: row.get(field) for field in fields}) for row in rows]

	def get_doc(self, doctype, name=None):
		if isinstance(doctype, dict):
			values = dict(doctype)
		else:
			values = {"doctype": doctype, **self.frappe.db.rows(doctype, name)[0]}
		return FakeDocument(_frappe=self.frappe, **values)

	def role_links(self):
		links = []
		for doctype, rows in self.frappe.db.tables.items():
			for row in rows:
				if row.get("role") == "Membership Reviewer":
					links.append({"reference_doctype": row.get("parenttype") or doctype})
				elif (
					row.get("allow_edit") == "Membership Reviewer"
					or row.get("allowed") == "Membership Reviewer"
				):
					links.append({"reference_doctype": "Workflow"})
		return links

	def assert_no_links(self, links):
		if links:
			raise self.frappe.LinkExistsError()

	def test_migrates_users_profiles_permissions_and_workflow_without_saving_users(self):
		self.add_role("staff@example.com", "Membership Reviewer")
		self.add_role("staff@example.com", "Sales User")
		self.add_role("Association staff", "Membership Reviewer", parenttype="Role Profile")
		self.add_role("Association staff", "Accounts User", parenttype="Role Profile")
		self.add("User Role Profile", parent="staff@example.com", role_profile="Association staff")
		permission = self.add(
			"Custom DocPerm",
			parent="Association Member",
			role="Membership Reviewer",
			read=1,
			write=0,
			if_owner=1,
		)
		state = self.add(
			"Workflow Document State", parent="Association Member Approval", allow_edit="Membership Reviewer"
		)
		transition = self.add(
			"Workflow Transition", parent="Association Member Approval", allowed="Membership Reviewer"
		)

		self.migration.execute()

		self.assertCountEqual(self.roles("staff@example.com"), ["Masters Manager", "Sales User"])
		self.assertCountEqual(
			self.roles("Association staff", "Role Profile"), ["Masters Manager", "Accounts User"]
		)
		self.assertEqual(permission["role"], "Masters Manager")
		self.assertEqual((permission["read"], permission["write"], permission["if_owner"]), (1, 0, 1))
		self.assertEqual(state["allow_edit"], "Masters Manager")
		self.assertEqual(transition["allowed"], "Masters Manager")
		self.assertEqual(self.frappe.db.get_value("Role", "Membership Reviewer", "disabled"), 1)
		self.assertEqual(self.frappe.db.get_value("Role", "Masters Manager", "desk_access"), 1)
		self.assertEqual(self.frappe.db.get_value("Role", "Association Member", "desk_access"), 0)
		self.assertEqual(self.frappe.saved_doctypes, ["Role"])

		before = copy.deepcopy(self.frappe.db.tables)
		self.migration.execute()
		self.assertEqual(self.frappe.db.tables, before)

	def test_deduplicates_existing_manager_role(self):
		self.add_role("staff@example.com", "Membership Reviewer")
		self.add_role("staff@example.com", "Masters Manager")
		self.migration.execute()
		self.assertEqual(self.roles("staff@example.com"), ["Masters Manager"])

	def test_retains_foreign_permissions_and_legacy_assignments(self):
		self.add_role("staff@example.com", "Membership Reviewer")
		self.add_role("Association staff", "Membership Reviewer", parenttype="Role Profile")
		foreign = self.add("Custom DocPerm", parent="Sales Order", role="Membership Reviewer", read=1)
		self.migration.execute()
		self.assertCountEqual(self.roles("staff@example.com"), ["Membership Reviewer", "Masters Manager"])
		self.assertCountEqual(
			self.roles("Association staff", "Role Profile"), ["Membership Reviewer", "Masters Manager"]
		)
		self.assertEqual(foreign["role"], "Membership Reviewer")
		self.assertEqual(self.frappe.db.get_value("Role", "Membership Reviewer", "disabled"), 0)
		before = copy.deepcopy(self.frappe.db.tables)
		self.migration.execute()
		self.assertEqual(self.frappe.db.tables, before)

	def test_migrates_only_app_owned_navigation(self):
		self.add("Workspace", name="Masters", module="Masters Association")
		self.add("Workspace", name="Sales", module="Selling")
		self.add_role("Masters", "Membership Reviewer", parenttype="Workspace")
		self.add_role("Sales", "Membership Reviewer", parenttype="Workspace")
		self.migration.execute()
		self.assertEqual(self.roles("Masters", "Workspace"), ["Masters Manager"])
		self.assertEqual(self.roles("Sales", "Workspace"), ["Membership Reviewer"])
		self.assertEqual(self.frappe.db.get_value("Role", "Membership Reviewer", "disabled"), 0)

	def test_dynamic_reference_keeps_legacy_role_active(self):
		self.add_role("staff@example.com", "Membership Reviewer")
		self.dynamic_links.append({"reference_doctype": "Custom Access Rule"})
		self.migration.execute()
		self.assertCountEqual(self.roles("staff@example.com"), ["Membership Reviewer", "Masters Manager"])
		self.assertEqual(self.frappe.db.get_value("Role", "Membership Reviewer", "disabled"), 0)

	def test_fresh_install_only_creates_roles(self):
		self.frappe.db.tables["Role"] = []
		self.migration.execute()
		self.assertEqual(self.get_all("Role", pluck="name"), ["Masters Manager", "Association Member"])
		self.assertEqual(self.frappe.saved_doctypes, [])


if __name__ == "__main__":
	unittest.main()
