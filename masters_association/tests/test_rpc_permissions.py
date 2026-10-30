"""Request-dispatch regression tests; no external RPC is executed."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from werkzeug.routing import Map, Rule
from werkzeug.test import EnvironBuilder
from werkzeug.wrappers import Request

QUALITY_CHILDREN = "erpnext.quality_management.doctype.quality_procedure.quality_procedure.get_children"


class AttrDict(dict):
	__getattr__ = dict.get
	__setattr__ = dict.__setitem__


class RPCPermissionError(Exception):
	pass


def endpoint(version, name="handle_rpc_call"):
	def never_called(**arguments):
		raise AssertionError("A policy test must never execute an RPC")

	never_called.__name__ = name
	never_called.__module__ = "frappe.api." + version
	return never_called


class TestRPCScope(unittest.TestCase):
	def setUp(self):
		self.frappe = types.ModuleType("frappe")
		self.frappe._ = lambda message: message
		self.frappe.PermissionError = RPCPermissionError
		self.frappe.throw = Mock(
			side_effect=lambda message, exception: self.fail_permission(message, exception)
		)
		self.frappe.local = AttrDict()
		self.frappe.session = AttrDict(user="member@example.com")
		self.frappe.form_dict = AttrDict()
		self.frappe.conf = AttrDict()
		self.roles = {"Association Member", "All", "Guest"}
		self.frappe.get_roles = Mock(side_effect=lambda user: list(self.roles))
		self.frappe.get_installed_apps = Mock(
			return_value=["frappe", "erpnext", "masters_association", "other_app"]
		)
		self.frappe.override_whitelisted_method = Mock(side_effect=lambda method: method)
		self.frappe.get_hooks = Mock(return_value={})
		self.permissions = []
		self.frappe.get_meta = Mock(side_effect=lambda doctype: AttrDict(permissions=self.permissions))
		api = types.ModuleType("frappe.api")
		native_upload = endpoint("v2", "upload_file")
		native_upload.__module__ = "frappe.handler"
		api.API_URL_MAP = Map(
			[
				Rule("/api/method/<path:method>", endpoint=endpoint("v1")),
				Rule("/api/v1/method/<path:method>", endpoint=endpoint("v1")),
				Rule("/api/v2/method/login", endpoint=endpoint("v2", "login")),
				Rule("/api/v2/method/upload_file", endpoint=native_upload),
				Rule("/api/v2/method/<method>", endpoint=endpoint("v2")),
				Rule("/api/v2/method/<doctype>/<method>", endpoint=endpoint("v2")),
				Rule("/api/v2/document/<doctype>", endpoint=endpoint("v2", "document_list")),
			]
		)
		modules = types.ModuleType("frappe.modules.utils")
		modules.get_doctype_module = Mock(return_value="Quality Management")
		modules.get_module_name = Mock(return_value=QUALITY_CHILDREN.rsplit(".", 1)[0])
		self.doctype_module = modules.get_doctype_module
		permissions = types.ModuleType("masters_association.permissions")
		permissions.MASTERS_ROLES = frozenset({"Association Member", "Masters Manager"})
		permissions.AUTOMATIC_ROLES = frozenset({"All", "Guest", "Desk User", "Administrator"})
		self.module_patch = patch.dict(
			sys.modules,
			{
				"frappe": self.frappe,
				"frappe.api": api,
				"frappe.modules.utils": modules,
				"masters_association.permissions": permissions,
			},
		)
		self.module_patch.start()
		self.addCleanup(self.module_patch.stop)
		spec = importlib.util.spec_from_file_location(
			"_masters_rpc_permissions_test", Path(__file__).resolve().parents[1] / "rpc_permissions.py"
		)
		self.guard = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(self.guard)

	def fail_permission(self, message, exception):
		raise exception(message)

	def request(self, path="/api/method/" + QUALITY_CHILDREN, http_method="GET", **form):
		self.frappe.local.request = Request(EnvironBuilder(path=path, method=http_method).get_environ())
		self.frappe.form_dict = AttrDict(form)

	def grant(self, **changes):
		grant = {"doctype": "Quality Procedure", "permission": "read", "roles": ["Quality Reader"]}
		grant.update(changes)
		self.frappe.conf.masters_external_rpc_permissions = {QUALITY_CHILDREN: grant}
		return grant

	def role_permission(self, role="Quality Reader", **changes):
		row = AttrDict(role=role, permlevel=0, if_owner=0, read=1)
		row.update(changes)
		self.permissions.append(row)
		return row

	def assert_denied(self):
		with self.assertRaises(RPCPermissionError):
			self.guard.check_rpc_scope()

	def test_unchecked_quality_get_children_is_blocked_for_both_scoped_roles(self):
		self.request()
		for role in ("Association Member", "Masters Manager"):
			with self.subTest(role=role):
				self.roles = {role, "All", "Guest", "Desk User"}
				self.assert_denied()
		self.frappe.get_meta.assert_not_called()

	def test_cookie_or_api_key_identity_uses_the_current_authenticated_user(self):
		self.request()
		self.assert_denied()
		self.frappe.get_roles.assert_called_once_with("member@example.com")

	def test_mcp_is_denied_for_scoped_users_including_trailing_slash(self):
		for role in ("Association Member", "Masters Manager"):
			self.roles = {role, "All", "Guest", "Desk User"}
			for path in ("/api/v2/mcp", "/api/v2/mcp/"):
				with self.subTest(role=role, path=path):
					self.request(path, http_method="POST")
					self.assert_denied()

	def test_mcp_behavior_is_preserved_for_administrators_and_unscoped_users(self):
		for user, roles in (
			("Administrator", {"Masters Manager"}),
			("admin@example.com", {"System Manager", "Masters Manager"}),
			("staff@example.com", {"Quality Reader", "Desk User"}),
		):
			with self.subTest(user=user):
				self.frappe.session.user = user
				self.roles = roles
				self.request("/api/v2/mcp", http_method="POST")
				self.guard.check_rpc_scope()

	def test_explicit_document_role_does_not_implicitly_enable_rpc(self):
		self.request()
		self.roles.add("Quality Reader")
		self.role_permission()
		self.assert_denied()

	def test_no_request_guests_administrators_and_unscoped_users_are_preserved(self):
		self.guard.check_rpc_scope()
		self.request()
		for user, roles in (
			("Guest", {"Guest"}),
			("Administrator", {"Masters Manager"}),
			("admin@example.com", {"System Manager", "Association Member"}),
			("staff@example.com", {"Quality Reader", "Desk User"}),
		):
			with self.subTest(user=user):
				self.frappe.session.user = user
				self.roles = roles
				self.guard.check_rpc_scope()

	def test_framework_masters_rest_and_unknown_routes_are_preserved(self):
		for path in (
			"/api/method/frappe.auth.get_logged_user",
			"/api/v2/method/login",
			"/api/v2/method/masters_association.member_portal.get_my_profile",
			"/api/v2/document/Quality%20Procedure",
			"/api/missing/route",
			"/member/profile",
			"/api/method/not_installed.api.method",
		):
			with self.subTest(path=path):
				self.request(path)
				self.guard.check_rpc_scope()
		self.frappe.get_meta.assert_not_called()

	def test_form_cmd_overrides_even_a_safe_v2_path(self):
		self.request("/api/v2/method/frappe.auth.get_logged_user", cmd=QUALITY_CHILDREN)
		self.assert_denied()
		self.frappe.override_whitelisted_method.assert_called_once_with(QUALITY_CHILDREN)

	def test_v1_paths_trim_backward_compatible_trailing_method_segments(self):
		for prefix in ("/api/method/", "/api/v1/method/"):
			with self.subTest(prefix=prefix):
				self.request(prefix + QUALITY_CHILDREN + "/extra")
				self.assert_denied()
				self.assertEqual(self.frappe.override_whitelisted_method.call_args.args[0], QUALITY_CHILDREN)

	def test_v2_dotted_and_short_doctype_methods_resolve_the_actual_rpc(self):
		for path in (
			"/api/v2/method/" + QUALITY_CHILDREN,
			"/api/v2/method/Quality%20Procedure/get_children",
		):
			with self.subTest(path=path):
				self.request(path)
				self.assert_denied()
				self.assertEqual(self.frappe.override_whitelisted_method.call_args.args[0], QUALITY_CHILDREN)
		self.doctype_module.assert_called_once_with("Quality Procedure")

	def test_framework_alias_cannot_hide_an_external_override(self):
		self.request("/api/v2/method/frappe.client.safe_alias")
		self.frappe.override_whitelisted_method.side_effect = lambda method: QUALITY_CHILDREN
		self.assert_denied()

	def test_tree_wrapper_cannot_bypass_quality_children_denial(self):
		self.request("/api/v2/method/frappe.desk.treeview.get_all_nodes", tree_method=QUALITY_CHILDREN)
		self.assert_denied()

	def test_upload_wrappers_including_native_v2_route_check_callbacks(self):
		for path, form in (
			("/api/method/frappe.handler.upload_file", {}),
			("/api/v2/method/upload_file", {}),
			("/", {"cmd": "upload_file"}),
		):
			with self.subTest(path=path, form=form):
				self.request(path, method=QUALITY_CHILDREN, **form)
				self.assert_denied()

	def test_search_wrappers_check_explicit_and_hook_selected_queries(self):
		for method in ("search_link", "search_widget"):
			with self.subTest(method=method):
				self.request("/api/method/frappe.desk.search." + method, query=QUALITY_CHILDREN)
				self.assert_denied()
		self.frappe.get_hooks.return_value = {"Quality Procedure": [QUALITY_CHILDREN]}
		self.request("/api/method/frappe.desk.search.search_link", doctype="Quality Procedure")
		self.assert_denied()

	def test_nested_framework_wrapper_does_not_hide_external_callback(self):
		self.request(
			"/api/method/frappe.desk.treeview.get_all_nodes",
			tree_method="frappe.desk.search.search_widget",
			query=QUALITY_CHILDREN,
		)
		self.assert_denied()

	def test_wrapper_callbacks_require_the_same_exact_business_grant(self):
		self.request("/api/v2/method/upload_file", method=QUALITY_CHILDREN)
		self.grant()
		self.roles.add("Quality Reader")
		self.role_permission()
		self.guard.check_rpc_scope()
		self.frappe.override_whitelisted_method.assert_not_called()

	def test_callback_override_semantics_match_the_actual_wrapper(self):
		self.frappe.override_whitelisted_method.side_effect = (
			lambda method: "frappe.client.get" if method == QUALITY_CHILDREN else method
		)
		self.request("/api/method/frappe.desk.treeview.get_all_nodes", tree_method=QUALITY_CHILDREN)
		self.guard.check_rpc_scope()  # Tree applies the override to its callback.
		self.request("/api/v2/method/upload_file", method=QUALITY_CHILDREN)
		self.assert_denied()  # Upload calls the supplied callback directly.
		self.request("/api/method/frappe.desk.search.search_link", query=QUALITY_CHILDREN)
		self.assert_denied()  # Search also calls the supplied query directly.

	def test_bad_callback_types_fail_closed(self):
		for wrapper, key in (
			("frappe.desk.treeview.get_all_nodes", "tree_method"),
			("frappe.handler.upload_file", "method"),
			("frappe.desk.search.search_link", "query"),
		):
			for value in ({}, [], 1, False):
				with self.subTest(wrapper=wrapper, value=value):
					self.request("/api/method/" + wrapper, **{key: value})
					self.assert_denied()

	def test_framework_wrappers_without_external_callbacks_are_preserved(self):
		for path in (
			"/api/v2/method/upload_file",
			"/api/method/frappe.handler.upload_file",
			"/api/method/frappe.desk.search.search_link",
		):
			with self.subTest(path=path):
				self.request(path)
				self.guard.check_rpc_scope()

	def test_exact_configuration_and_matching_effective_role_grant_allow_rpc(self):
		self.request()
		self.roles.add("Quality Reader")
		self.grant()
		self.role_permission()
		self.guard.check_rpc_scope()
		self.frappe.get_meta.assert_called_once_with("Quality Procedure")

	def test_prefix_or_unrelated_method_configuration_does_not_allow_rpc(self):
		self.request()
		self.roles.add("Quality Reader")
		grant = self.grant()
		self.role_permission()
		for key in ("erpnext", QUALITY_CHILDREN.rsplit(".", 1)[0] + ".*", QUALITY_CHILDREN + "_other"):
			with self.subTest(key=key):
				self.frappe.conf.masters_external_rpc_permissions = {key: grant}
				self.assert_denied()

	def test_wrong_roles_operation_level_and_owner_only_grants_are_denied(self):
		self.request()
		self.grant()
		for user_roles, row in (
			({"Sales User"}, {"role": "Sales User"}),
			({"Quality Reader", "Sales User"}, {"role": "Sales User"}),
			({"Quality Reader"}, {"role": "Quality Reader", "read": 0, "write": 1}),
			({"Quality Reader"}, {"role": "Quality Reader", "permlevel": 1}),
			({"Quality Reader"}, {"role": "Quality Reader", "if_owner": 1}),
		):
			with self.subTest(user_roles=user_roles, row=row):
				self.roles = {"Association Member", "All", "Guest"} | user_roles
				self.permissions.clear()
				self.role_permission(**row)
				self.assert_denied()

	def test_automatic_and_masters_roles_cannot_authorize_external_rpc(self):
		self.request()
		for role in ("All", "Guest", "Desk User", "Association Member", "Masters Manager"):
			with self.subTest(role=role):
				self.roles = {"Association Member", role}
				self.grant(roles=[role])
				self.permissions.clear()
				self.role_permission(role=role)
				self.assert_denied()

	def test_malformed_configuration_fails_closed(self):
		self.request()
		self.roles.add("Quality Reader")
		self.role_permission()
		for changes in (
			{"doctype": ""},
			{"doctype": {}},
			{"roles": "Quality Reader"},
			{"roles": []},
			{"roles": [{}]},
			{"permission": "unknown"},
			{"permission": {}},
		):
			with self.subTest(changes=changes):
				self.grant(**changes)
				self.assert_denied()
		for configuration in ([], None, {QUALITY_CHILDREN: True}):
			self.frappe.conf.masters_external_rpc_permissions = configuration
			self.assert_denied()


if __name__ == "__main__":
	unittest.main()
