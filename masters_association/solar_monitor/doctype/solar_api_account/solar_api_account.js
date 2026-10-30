// Desk is read-only for Solar Monitor; members manage their own accounts in the portal.
frappe.ui.form.on("Solar API Account", {
	refresh(frm) {
		frm.disable_form();
		frm.add_custom_button(__("Open Solar Portal"), () => window.open("/solar", "_blank"));
	},
});
