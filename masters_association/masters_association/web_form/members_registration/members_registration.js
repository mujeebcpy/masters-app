frappe.ready(function() {
	frappe.web_form.validate = () => {
    const gstin = (frappe.web_form.get_value("gst") || "")
        .trim()
        .toUpperCase();

    // Leave blank if GSTIN is optional.
    if (!gstin) return true;

    // Basic format for a regular PAN-based GSTIN.
    const pattern =
        /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/;

    if (!pattern.test(gstin)) {
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

    frappe.web_form.set_value("gstin", gstin);
    return true;
};
	// bind events here
})