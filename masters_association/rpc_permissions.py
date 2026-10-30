"""Close unchecked external-app RPC paths for narrowly scoped Masters accounts.

Document permissions still secure standard REST and Frappe methods. External
whitelisted methods may bypass them, so an administrator must separately opt
in each audited RPC and its required business permission.
"""

import frappe
from frappe import _
from werkzeug.exceptions import HTTPException

from masters_association.permissions import AUTOMATIC_ROLES, MASTERS_ROLES

CORE_APPS = frozenset({"frappe", "masters_association"})
PERMISSION_TYPES = frozenset(
	{
		"read",
		"write",
		"create",
		"delete",
		"submit",
		"cancel",
		"amend",
		"print",
		"email",
		"report",
		"import",
		"export",
		"share",
		"select",
	}
)


def _requested_rpc_method(request):
	# application() dispatches cmd before matching API routes, including on v2 URLs.
	if cmd := frappe.form_dict.get("cmd"):
		return (cmd, True) if isinstance(cmd, str) else None
	if not request.path.startswith("/api/"):
		return None

	from frappe.api import API_URL_MAP

	try:
		endpoint, arguments = API_URL_MAP.bind_to_environ(request.environ).match()
	except HTTPException:
		return None  # Preserve the normal framework 404/405/redirect response.
	if endpoint.__module__ == "frappe.handler" and endpoint.__name__ == "upload_file":
		# The dedicated v2 upload route calls its function directly, without overrides.
		return "frappe.handler.upload_file", False
	if endpoint.__name__ != "handle_rpc_call" or endpoint.__module__ not in (
		"frappe.api.v1",
		"frappe.api.v2",
	):
		return None
	method = arguments.get("method")
	if endpoint.__module__ == "frappe.api.v1":
		return method.split("/", 1)[0], True
	if doctype := arguments.get("doctype"):
		from frappe.modules.utils import get_doctype_module, get_module_name

		# Mirror load_doctype_module's path without importing an external controller.
		method = get_module_name(doctype, get_doctype_module(doctype)) + "." + method
	return method, True


def _deny():
	frappe.throw(
		_(
			"This account cannot call this application's method. An administrator must explicitly authorize it."
		),
		frappe.PermissionError,
	)


def _delegated_rpc(method):
	"""Mirror the narrowly defined callbacks in standard Frappe RPC wrappers."""
	if method == "frappe.desk.treeview.get_all_nodes":
		callback, use_override = frappe.form_dict.get("tree_method"), True
	elif method in ("frappe.handler.upload_file", "upload_file"):
		callback, use_override = frappe.form_dict.get("method"), False
	elif method in ("frappe.desk.search.search_link", "frappe.desk.search.search_widget"):
		callback, use_override = frappe.form_dict.get("query"), False
		if callback is None or callback == "":
			doctype = frappe.form_dict.get("doctype")
			if doctype is not None and not isinstance(doctype, str):
				_deny()
			standard_queries = frappe.get_hooks("standard_queries") or {}
			if isinstance(standard_queries, dict) and doctype in standard_queries:
				queries = standard_queries[doctype]
				if not isinstance(queries, list) or not queries:
					_deny()
				callback = queries[-1]
	else:
		return None
	if callback is None or callback == "":
		return None
	if not isinstance(callback, str):
		_deny()
	return callback, use_override


def _has_external_rpc_grant(method, roles):
	configuration = frappe.conf.get("masters_external_rpc_permissions", {})
	if not isinstance(configuration, dict) or not isinstance(configuration.get(method), dict):
		return False
	grant = configuration[method]
	doctype = grant.get("doctype")
	permission = grant.get("permission")
	allowed_roles = grant.get("roles")
	if (
		not isinstance(doctype, str)
		or not doctype.strip()
		or not isinstance(permission, str)
		or permission not in PERMISSION_TYPES
		or not isinstance(allowed_roles, list)
		or not allowed_roles
		or not all(isinstance(role, str) for role in allowed_roles)
	):
		return False
	applicable_roles = roles.intersection(allowed_roles).difference(AUTOMATIC_ROLES | MASTERS_ROLES)
	if not applicable_roles:
		return False

	# Effective metadata includes Custom DocPerm overrides. An owner-only role
	# cannot safely authorize an unchecked endpoint which may return other rows.
	return any(
		row.role in applicable_roles
		and not row.get("permlevel")
		and not row.get("if_owner")
		and (row.get(permission) or (permission == "select" and row.get("read")))
		for row in frappe.get_meta(doctype).permissions
	)


def check_rpc_scope():
	"""auth_hooks entry: enforce scope after cookie/OAuth/API-key authentication."""
	request = getattr(frappe.local, "request", None)
	if request is None or request.method == "OPTIONS":
		return
	user = frappe.session.user
	if user in ("Guest", "Administrator"):
		return
	roles = frozenset(frappe.get_roles(user))
	if "System Manager" in roles or not roles.intersection(MASTERS_ROLES):
		return
	if request.path.rstrip("/") == "/api/v2/mcp":
		frappe.throw(_("MCP access is not available for scoped Masters accounts."), frappe.PermissionError)
	rpc = _requested_rpc_method(request)
	if not rpc:
		return
	seen = set()
	while rpc:
		method, use_override = rpc
		if use_override:
			method = frappe.override_whitelisted_method(method)
		if not isinstance(method, str):
			_deny()
		if method in seen:
			return  # A cyclic wrapper cannot add another unchecked callback.
		seen.add(method)
		if "." in method:
			app = method.split(".", 1)[0]
			if (
				app not in CORE_APPS
				and app in frappe.get_installed_apps()
				and not _has_external_rpc_grant(method, roles)
			):
				_deny()
		rpc = _delegated_rpc(method)
