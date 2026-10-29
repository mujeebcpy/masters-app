import frappe


def execute():
	"""Drop the old Membership navigation, replaced by the Masters workspace and sidebar.

	The standard Workspace and Desktop Icon go with migrate's orphan cleanup once their files
	are gone, but the site-level Sidebar and Workspace Sidebar copies do not.
	"""
	owned_by_app = {
		"Workspace": {"module": "Masters Association"},
		"Sidebar": {"module": "Masters Association"},
		"Workspace Sidebar": {"app": "masters_association"},
		"Desktop Icon": {"app": "masters_association"},
	}
	for doctype, filters in owned_by_app.items():
		if frappe.db.exists(doctype, {"name": "Membership", **filters}):
			frappe.delete_doc(doctype, "Membership", ignore_permissions=True, force=True)
