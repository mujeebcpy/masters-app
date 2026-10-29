# Copyright (c) 2026, mujeebcpy and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AssociationMember(Document):
	def before_insert(self):
		# frappe.flags.in_web_form is only set while the Web Form's `accept`
		# handler is creating the document, so this stays unchecked for
		# records created from the desk, Data Import, or the API directly.
		self.submitted_via_web_form = 1 if frappe.flags.in_web_form else 0

	def on_update(self):
		# Resolving the link can take a few network round trips, so keep it off the save
		if self.has_value_changed("google_maps_link") and (self.google_maps_link or self.location):
			frappe.enqueue(
				"masters_association.geo.update_member_location",
				member=self.name,
				enqueue_after_commit=True,
				deduplicate=True,
				job_id=f"member_location::{self.name}",
			)
