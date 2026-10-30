"""Restrict Masters accounts without replacing Frappe's permission system.

Automatic roles can carry permissions from installed business apps. Masters
accounts need an explicit role grant on those DocTypes instead. These hooks
only remove access: normal roles, User Permissions and document shares still
apply. Permission-bypassing SQL/get_all in another app remains that app's
responsibility.
"""

import frappe

MASTERS_ROLES = frozenset({"Masters Manager", "Association Member"})
AUTOMATIC_ROLES = frozenset({"All", "Guest", "Desk User", "Administrator"})

# Shared framework services needed by Desk, authentication, attachments and
# ordinary self-service. Exempting a service preserves its existing checks;
# it does not grant a Masters account permission to manage that service.
FRAMEWORK_INFRASTRUCTURE = frozenset(
	{
		"Address",
		"Calendar View",
		"Comment",
		"Communication",
		"Contact",
		"Country",
		"Custom Field",
		"Custom Sidebar",
		"Desktop Icon",
		"Desktop Layout",
		"DocField",
		"DocPerm",
		"DocType",
		"Dock",
		"Document Follow",
		"File",
		"Form Tour",
		"Gender",
		"Global Search Settings",
		"Language",
		"List Filter",
		"Module Def",
		"Module Onboarding",
		"Module Profile",
		"Notification Log",
		"Notification Settings",
		"Onboarding Step",
		"Print Format",
		"Print Heading",
		"Role",
		"Role Profile",
		"Salutation",
		"Sidebar",
		"Tag",
		"Tag Link",
		"ToDo",
		"User",
		"User Permission",
		"Workflow",
		"Workflow Action",
		"Workflow State",
		"Workspace",
		"Workspace Sidebar",
	}
)


def _scoped_roles(user):
	roles = frozenset(frappe.get_roles(user))
	if user == "Administrator" or "System Manager" in roles or not roles.intersection(MASTERS_ROLES):
		return None
	return roles


def _preserve_framework_or_masters(doctype):
	return doctype in FRAMEWORK_INFRASTRUCTURE or frappe.get_doctype_app(doctype) == "masters_association"


def _explicit_permissions(meta, roles, ptype):
	"""Use effective metadata, so site Custom DocPerm overrides are respected."""
	explicit_roles = roles.difference(AUTOMATIC_ROLES | MASTERS_ROLES)
	return [
		permission
		for permission in meta.permissions
		if permission.role in explicit_roles
		and not permission.get("permlevel")
		and (permission.get(ptype) or (ptype == "select" and permission.get("read")))
	]


def has_scoped_permission(doc, ptype=None, user=None, debug=False):
	"""Wildcard document permission hook; never grants an underlying permission."""
	user = user or frappe.session.user
	roles = _scoped_roles(user)
	if roles is None or _preserve_framework_or_masters(doc.doctype):
		return True

	permissions = _explicit_permissions(frappe.get_meta(doc.doctype), roles, ptype or "read")
	return any(not row.get("if_owner") or doc.get("owner") == user for row in permissions)


def get_scoped_query_conditions(user=None, doctype=None):
	"""Wildcard list hook supported by both Frappe v16 query engines.

	List hooks do not receive the requested operation. Fail closed if an
	automatic read grant would promote an explicit select-only grant to full
	read access; an administrator can grant explicit read for that DocType.
	Frappe adds deliberately shared documents through its normal share rules.
	"""
	user = user or frappe.session.user
	roles = _scoped_roles(user)
	if not doctype or roles is None or _preserve_framework_or_masters(doctype):
		return ""

	meta = frappe.get_meta(doctype)
	permissions = _explicit_permissions(meta, roles, "read")
	if not permissions:
		automatic_read = any(
			row.role in roles.intersection(AUTOMATIC_ROLES | MASTERS_ROLES)
			and not row.get("permlevel")
			and row.get("read")
			for row in meta.permissions
		)
		if automatic_read:
			return "1=0"
		permissions = _explicit_permissions(meta, roles, "select")

	if not permissions:
		return "1=0"
	if any(not row.get("if_owner") for row in permissions):
		return ""

	# DocType names come from framework metadata; escape the SQL identifier too.
	table = ("tab" + doctype).replace("`", "``")
	return f"`{table}`.`owner` = {frappe.db.escape(user)}"
