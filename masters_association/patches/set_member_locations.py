import frappe

from masters_association.geo import update_member_location


def execute():
	for member in frappe.get_all(
		"Association Member",
		filters={"google_maps_link": ("is", "set"), "location": ("is", "not set")},
		pluck="name",
	):
		update_member_location(member)
