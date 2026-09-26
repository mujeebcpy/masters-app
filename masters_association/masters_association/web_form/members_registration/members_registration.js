frappe.ready(function() {
	// Basic format for a regular PAN-based GSTIN.
	const gstin_pattern = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

	function ensure_mobile_country_code() {
		const field = frappe.web_form.get_field("mobile_no_whatsapp");
		const value = (frappe.web_form.get_value("mobile_no_whatsapp") || "").trim();

		// Leave empty numbers to mandatory validation and preserve international numbers.
		if (!value || /^\+\d/.test(value)) return true;

		if (
			field?.country_codes &&
			field.country_code_picker &&
			field.selected_icon?.length &&
			field.$isd?.length &&
			field.$input?.length
		) {
			const country_code = field.$isd.text().trim() || "+91";
			// Web Form validate is synchronous; set_value would finish after submission.
			field.set_input(`${country_code}-${value}`);
		}

		if (/^\+\d/.test(frappe.web_form.get_value("mobile_no_whatsapp") || "")) {
			return true;
		}

		frappe.msgprint({
			title: __("Country Code Required"),
			message: __("Please select country code for Mobile Number"),
			indicator: "red"
		});
		return false;
	}

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

	frappe.web_form.validate = () => {
		if (!ensure_mobile_country_code()) return false;

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
