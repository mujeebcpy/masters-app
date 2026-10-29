# Copyright (c) 2026, mujeebcpy and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from masters_association.geo import (
	MAPS_LINK_HELP,
	coordinates_from_maps_link,
	is_search_share_link,
	point_geojson,
)


class AssociationMember(Document):
	def before_insert(self):
		# frappe.flags.in_web_form is only set while the Web Form's `accept`
		# handler is creating the document, so this stays unchecked for
		# records created from the desk, Data Import, or the API directly.
		self.submitted_via_web_form = 1 if frappe.flags.in_web_form else 0

	def validate(self):
		self.validate_google_maps_link()
		self.set_location()

	def validate_google_maps_link(self):
		# Only on change, so existing members with such links can still be approved and edited
		if self.has_value_changed("google_maps_link") and is_search_share_link(self.google_maps_link):
			message = _("This is a Google Search share link, which doesn't include your location.")
			frappe.throw(f"{message}<br><br>{_(MAPS_LINK_HELP)}", title=_("Use a Google Maps link"))

	def set_location(self):
		# Resolved during the save rather than in a background job, so the form gets the pin back
		# with the saved doc instead of keeping a stale Location it would write back on the next save.
		# A link that couldn't be resolved before is retried, so re-saving fixes a missing pin.
		if is_search_share_link(self.google_maps_link):
			return
		if self.has_value_changed("google_maps_link") or (self.google_maps_link and not self.location):
			coordinates = coordinates_from_maps_link(self.google_maps_link)
			self.location = point_geojson(*coordinates) if coordinates else None
