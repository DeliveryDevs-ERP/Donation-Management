// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Donor", {
	refresh(frm) {
		toggle_trustee_reference(frm);
	},

	customer_type(frm) {
		toggle_trustee_reference(frm);
		if (frm.doc.customer_type === "Walk-in") {
			set_value_if_changed(frm, "referred_by_trustee", "");
		}
	},
});

function toggle_trustee_reference(frm) {
	const is_referred_by_trustee = frm.doc.customer_type === "Refered by Trustee";
	frm.toggle_display("referred_by_trustee", is_referred_by_trustee);
	frm.toggle_reqd("referred_by_trustee", is_referred_by_trustee);
}

function set_value_if_changed(frm, fieldname, value) {
	const current_value = frm.doc[fieldname] || "";
	const new_value = value || "";

	if (String(current_value) !== String(new_value)) {
		frm.set_value(fieldname, value);
	}
}
