// Copyright (c) 2026, mujeebcpy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Association Member", {
	gst(frm) {
		const gstin_pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;
		const gstin = (frm.doc.gst || "").trim().toUpperCase();

		if (gstin !== frm.doc.gst) {
			frm.set_value("gst", gstin);
		}

		if (!gstin) {
			frm.set_value("gst_company_name", "");
			frm.set_value("gst_address", "");
			frm.set_value("gst_pincode", "");
			frm.set_value("gst_state", "");
			frm.set_value("gst_status", "");
			return;
		}

		if (!gstin_pattern.test(gstin)) return;

		frappe.call({
			method: "masters_association.api.fetch_gst_details",
			args: { gstin },
			freeze: true,
			freeze_message: __("Fetching GST details..."),
			callback: function(r) {
				if (!r.message) return;
				frm.set_value("gst_company_name", r.message.gst_company_name);
				frm.set_value("gst_address", r.message.gst_address);
				frm.set_value("gst_pincode", r.message.gst_pincode);
				frm.set_value("gst_state", r.message.gst_state);
				frm.set_value("gst_status", r.message.gst_status);
			},
		});
	},
});
