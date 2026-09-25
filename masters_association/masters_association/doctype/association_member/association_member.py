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
