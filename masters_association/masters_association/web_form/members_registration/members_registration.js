frappe.ready(function() {
	// Auto-fetch of GST details needs India Compliance's GST API to be
	// registered (GST Settings). Turn this back on once that's done.
	const GST_AUTOFILL_ENABLED = false;

	// Basic format for a regular PAN-based GSTIN.
	const gstin_pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

	function clear_gst_details() {
		frappe.web_form.set_value("gst_company_name", "");
		frappe.web_form.set_value("gst_address", "");
		frappe.web_form.set_value("gst_pincode", "");
		frappe.web_form.set_value("gst_state", "");
		frappe.web_form.set_value("gst_status", "");
	}

	function fetch_gst_details(gstin) {
		frappe.call({
			method: "masters_association.api.fetch_gst_details",
			args: { gstin },
			callback: function(r) {
				if (!r.message) return;
				frappe.web_form.set_value("gst_company_name", r.message.gst_company_name);
				frappe.web_form.set_value("gst_address", r.message.gst_address);
				frappe.web_form.set_value("gst_pincode", r.message.gst_pincode);
				frappe.web_form.set_value("gst_state", r.message.gst_state);
				frappe.web_form.set_value("gst_status", r.message.gst_status);
			}
		});
	}

	// Auto-fetch GST details as soon as a valid-looking GSTIN is entered.
	if (GST_AUTOFILL_ENABLED) {
		frappe.web_form.on("gst", (field, value) => {
			const gstin = (value || "").trim().toUpperCase();

			if (gstin !== value) {
				frappe.web_form.set_value("gst", gstin);
			}

			if (!gstin) {
				clear_gst_details();
				return;
			}

			if (gstin_pattern.test(gstin)) {
				fetch_gst_details(gstin);
			} else {
				clear_gst_details();
			}
		});
	}

	frappe.web_form.validate = () => {
		const gstin = (frappe.web_form.get_value("gst") || "")
			.trim()
			.toUpperCase();

		// Leave blank if GSTIN is optional.
		if (!gstin) return true;

		if (!gstin_pattern.test(gstin)) {
			frappe.msgprint({
				title: "Check your GSTIN",
				message:
					"Enter a 15-character GSTIN: two state-code digits, " +
					"your 10-character PAN, an entity code, Z, " +
					"and the final check character.",
				indicator: "red"
			});
			return false;
		}

		frappe.web_form.set_value("gst", gstin);
		return true;
	};
})