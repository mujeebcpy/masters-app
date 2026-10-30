// Desk is read-only for Solar Monitor; owners refresh production from the portal.
frappe.ui.form.on("Solar Station", {
	refresh(frm) {
		if (frm.is_new()) return;
		frm.add_custom_button(__("Open in Solar Portal"), () =>
			window.open(`/solar/station/${encodeURIComponent(frm.doc.name)}`, "_blank")
		);
	},
});
