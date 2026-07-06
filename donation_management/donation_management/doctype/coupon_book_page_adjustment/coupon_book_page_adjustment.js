// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Coupon Book Page Adjustment", {
	refresh(frm) {
		if (frm.is_new() || frm.doc.docstatus !== 1) {
			return;
		}

		const roles = frappe.user_roles || [];

		if (frm.doc.status === "Pending Donation Manager" && has_any_role(roles, ["Donation Manager", "System Manager"])) {
			frm.add_custom_button(__("Approve"), () => frm.call("approve_by_donation_manager"));
			frm.add_custom_button(__("Reject"), () => reject_request(frm), __("Actions"));
		}

		if (frm.doc.status === "Pending Finance Manager" && has_any_role(roles, ["Finance Manager", "System Manager"])) {
			frm.add_custom_button(__("Approve"), () => frm.call("approve_by_finance_manager"));
			frm.add_custom_button(__("Reject"), () => reject_request(frm), __("Actions"));
		}
	},
});

function has_any_role(user_roles, required_roles) {
	return required_roles.some((role) => user_roles.includes(role));
}

function reject_request(frm) {
	frappe.confirm(__("Reject this page adjustment request?"), () => {
		frm.call("reject_request").then(() => {
			frm.reload_doc();
			frappe.show_alert({ message: __("Request rejected"), indicator: "orange" });
		});
	});
}
