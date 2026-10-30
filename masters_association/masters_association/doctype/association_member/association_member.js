// Copyright (c) 2026, mujeebcpy and contributors
// For license information, please see license.txt

frappe.ui.form.on("Association Member", {
	refresh(frm) {
		const is_admin = frappe.session.user === "Administrator" || frappe.user.has_role("System Manager");
		const can_manage = is_admin || frappe.user.has_role("Masters Manager");
		frm.set_df_property("email", "read_only", Boolean(frm.doc.user));
		if (frm.is_new() || !can_manage) return;

		if (frm.doc.account_setup_error) {
			frm.set_intro(frappe.utils.escape_html(frm.doc.account_setup_error), "orange");
		} else if (frm.doc.user) {
			frm.set_intro(__("Linked account: {0}", [frappe.utils.escape_html(frm.doc.user)]), "green");
		}
		const eligible = frm.doc.portal_enabled && frm.doc.application_status === "Approved"
			&& ["Normal Member", "Lifetime Member"].includes(frm.doc.membership_status);
		if (!eligible) return;

		if (frm.doc.user) {
			frm.add_custom_button(__("Send Invitation"), () => member_account_action(frm, "send_member_invitation"), __("Member Account"));
		} else {
			frm.add_custom_button(
				frm.doc.account_setup_error ? __("Retry Account Setup") : __("Create User"),
				() => member_account_action(frm, "create_member_user"),
				__("Member Account")
			);
			if (is_admin) {
				frm.add_custom_button(__("Link Existing User"), () => select_member_user(frm), __("Member Account"));
			}
		}
	},

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

async function member_account_action(frm, action, args = {}) {
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save the member record before changing its account."));
		return;
	}
	const response = await frappe.call({
		method: `masters_association.member_portal.${action}`,
		args: { member_name: frm.doc.name, ...args },
		freeze: true,
		freeze_message: __("Updating member account..."),
	});
	if (response.message) {
		frappe.msgprint({
			message: frappe.utils.escape_html(response.message.message || ""),
			indicator: response.message.error ? "orange" : "green",
		});
	}
	await frm.reload_doc();
}

function select_member_user(frm) {
	if (frm.is_dirty()) {
		frappe.msgprint(__("Save the member record before linking a User."));
		return;
	}
	frappe.prompt(
		[{
			fieldname: "user", fieldtype: "Link", options: "User", label: __("Existing User"), reqd: 1,
			get_query: () => ({ filters: { enabled: 1, name: ["not in", ["Administrator", "Guest"]] } }),
		}],
		async ({ user }) => {
			const response = await frappe.call({
				method: "masters_association.member_portal.get_user_link_preview",
				type: "GET", args: { member_name: frm.doc.name, user }, freeze: true,
			});
			const preview = response.message;
			if (!preview) return;
			const escape = (value) => frappe.utils.escape_html(value || __("Not set"));
			const rows = [
				[__("Name"), preview.member.display_name, preview.user.display_name],
				[__("Email"), preview.member.email, preview.user.email],
				[__("Phone"), preview.member.phone, preview.user.phone],
				[__("Photo"), preview.member.photo, preview.user.photo],
			];
			const details = `<div class="table-responsive"><table class="table table-bordered">
				<thead><tr><th>${__("Detail")}</th><th>${__("Member")}</th><th>${__("Existing User")}</th></tr></thead>
				<tbody>${rows.map(([label, member_value, user_value]) => `<tr><td>${escape(label)}</td><td>${escape(member_value)}</td><td>${escape(user_value)}</td></tr>`).join("")}</tbody>
			</table></div>`;
			frappe.confirm(
				`${details}<p>${escape(preview.message)}</p><p>${__("Link this User to the member?")}</p>`,
				() => member_account_action(frm, "link_member_user", { user })
			);
		},
		__("Link Existing User"),
		__("Preview Link")
	);
}
