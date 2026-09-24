import frappe
from frappe import _


@frappe.whitelist(allow_guest=True)
def fetch_gst_details(gstin: str):
	"""Fetch registered business details for a GSTIN using India Compliance's GST Public API.

	Used by the Members Registration web form to auto-populate GST details, so it must
	work for guest/portal users, unlike India Compliance's own `get_gstin_info` API which
	is restricted to users with desk access.
	"""
	if not gstin or not gstin.strip():
		frappe.throw(_("GSTIN is required"))

	from india_compliance.gst_india.utils.gstin_info import _get_gstin_info

	try:
		# throw_error=True surfaces India Compliance's own errors (invalid GSTIN,
		# API not configured, GSP downtime, etc.), which are already safe,
		# human-readable ValidationErrors and more useful than a generic message.
		gstin_info = _get_gstin_info(gstin.strip().upper(), throw_error=True)
	except frappe.ValidationError:
		raise
	except Exception:
		frappe.log_error(title="Failed to fetch GST details")
		frappe.throw(_("GST lookup service is currently unavailable. Please fill the details manually or try again later."))

	if not gstin_info or not gstin_info.get("gstin"):
		frappe.throw(_("No details found for this GSTIN. Please verify the GSTIN or fill the details manually."))

	address = gstin_info.get("permanent_address") or {}
	address_line = ", ".join(
		part
		for part in (address.get("address_line1"), address.get("address_line2"), address.get("city"))
		if part
	)

	return {
		"gst_company_name": gstin_info.get("business_name"),
		"gst_address": address_line,
		"gst_pincode": address.get("pincode"),
		"gst_state": address.get("state"),
		"gst_status": gstin_info.get("status"),
	}
