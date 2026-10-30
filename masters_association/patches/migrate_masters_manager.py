"""Replace the app's reviewer role without saving Users or provisioning accounts."""

import frappe

OLD_ROLE = "Membership Reviewer"
MANAGER_ROLE = "Masters Manager"
MEMBER_ROLE = "Association Member"
MASTERS_DOCTYPES = (
	"Association Member",
	"Website Enquiry",
	"Gallery Item",
	"Association Event",
	"Association Document",
)
WORKFLOW = "Association Member Approval"


def execute():
	# Fixtures are synced after post-model-sync patches, so create the target roles first.
	ensure_role(MANAGER_ROLE, desk_access=1)
	ensure_role(MEMBER_ROLE, desk_access=0)

	if not frappe.db.exists("Role", OLD_ROLE):
		return

	# Custom DocPerm overrides standard permissions for the entire DocType. Retain its
	# existing rights and conditions, changing only the app-owned role reference.
	for permission_type in ("DocPerm", "Custom DocPerm"):
		for row in frappe.get_all(
			permission_type,
			filters={"role": OLD_ROLE, "parent": ("in", MASTERS_DOCTYPES)},
			fields=["name", "parent"],
		):
			frappe.db.set_value(permission_type, row.name, "role", MANAGER_ROLE, update_modified=False)
			frappe.clear_cache(doctype=row.parent)

	# This patch runs before fixture sync; update the existing app workflow now too.
	for doctype, role_field in (
		("Workflow Document State", "allow_edit"),
		("Workflow Transition", "allowed"),
	):
		for name in frappe.get_all(doctype, filters={"parent": WORKFLOW, role_field: OLD_ROLE}, pluck="name"):
			frappe.db.set_value(doctype, name, role_field, MANAGER_ROLE, update_modified=False)
	frappe.clear_document_cache("Workflow", WORKFLOW)

	assignments = frappe.get_all(
		"Has Role", filters={"role": OLD_ROLE}, fields=["name", "parent", "parenttype", "parentfield"]
	)
	for row in assignments:
		if row.parenttype not in ("User", "Role Profile") and is_app_owned(row.parenttype, row.parent):
			migrate_assignment(row)

	# A site may have reused this app's old role for another app. Keep those grants
	# and assignments intact until an administrator can separate their ownership.
	keep_legacy = has_external_role_references()
	affected_users = set()
	for row in assignments:
		if row.parenttype not in ("User", "Role Profile"):
			continue
		migrate_assignment(row, keep_legacy=keep_legacy)
		if row.parenttype == "User":
			affected_users.add(row.parent)
		else:
			affected_users.update(
				frappe.get_all("User Role Profile", filters={"role_profile": row.parent}, pluck="parent")
			)

	for user in affected_users:
		frappe.clear_cache(user=user)

	retire_legacy_role()


def ensure_role(name, *, desk_access):
	if not frappe.db.exists("Role", name):
		frappe.get_doc(
			{"doctype": "Role", "role_name": name, "desk_access": desk_access, "disabled": 0}
		).insert(ignore_permissions=True)


def migrate_assignment(row, *, keep_legacy=False):
	filters = {
		"parent": row.parent,
		"parenttype": row.parenttype,
		"parentfield": row.parentfield,
	}
	has_manager = frappe.db.exists("Has Role", {**filters, "role": MANAGER_ROLE})
	if keep_legacy:
		if not has_manager:
			indexes = frappe.get_all("Has Role", filters=filters, pluck="idx")
			frappe.get_doc(
				{
					"doctype": "Has Role",
					**filters,
					"role": MANAGER_ROLE,
					"idx": max(indexes, default=0) + 1,
				}
			).insert(ignore_permissions=True)
	elif has_manager:
		frappe.db.delete("Has Role", {"name": row.name})
	else:
		frappe.db.set_value("Has Role", row.name, "role", MANAGER_ROLE, update_modified=False)
	frappe.clear_document_cache(row.parenttype, row.parent)


def is_app_owned(doctype, name):
	"""Only migrate navigation references belonging to this app, never another app."""
	meta = frappe.get_meta(doctype)
	if meta.get_field("module"):
		return frappe.db.get_value(doctype, name, "module") == "Masters Association"
	if meta.get_field("app"):
		return frappe.db.get_value(doctype, name, "app") == "masters_association"
	return False


def has_external_role_references():
	from frappe.model.delete_doc import get_dynamic_linked_docs, get_linked_docs

	# Frappe's delete-link checker deliberately ignores navigation parents. Their
	# role filters still matter here, so inspect remaining Has Role rows explicitly.
	if any(
		row.parenttype not in ("User", "Role Profile")
		for row in frappe.get_all("Has Role", filters={"role": OLD_ROLE}, fields=["parenttype"])
	):
		return True
	role = frappe.get_doc("Role", OLD_ROLE)
	return any(
		link["reference_doctype"] not in ("User", "Role Profile")
		for link in (*get_linked_docs(role), *get_dynamic_linked_docs(role))
	)


def retire_legacy_role():
	"""Keep a legacy role active if another app or a site customization still uses it."""
	from frappe.model.delete_doc import check_if_doc_is_dynamically_linked, check_if_doc_is_linked

	if has_external_role_references():
		return
	role = frappe.get_doc("Role", OLD_ROLE)
	try:
		check_if_doc_is_linked(role)
		check_if_doc_is_dynamically_linked(role)
	except frappe.LinkExistsError:
		return

	if not role.disabled:
		role.disabled = 1
		role.save(ignore_permissions=True)
