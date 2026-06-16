// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Donor", {
	setup(frm) {
		frm.set_query("parent_donor", () => ({
			filters: {
				is_group: 1,
				name: ["!=", frm.doc.name || ""],
			},
		}));

		frm.set_query("referred_by_trustee", () => ({
			filters: {
				is_group: 1,
			},
		}));
	},

	refresh(frm) {
		toggle_donor_reference_fields(frm);
		add_donor_tree_button(frm);
	},

	customer_type(frm) {
		toggle_donor_reference_fields(frm);
		if (frm.doc.customer_type === "Walk-in") {
			set_value_if_changed(frm, "referred_by_trustee", "");
		}
		if (frm.doc.customer_type === "Refered by Trustee") {
			set_value_if_changed(frm, "parent_donor", "");
		}
	},
});

function toggle_donor_reference_fields(frm) {
	const is_referred_by_trustee = frm.doc.customer_type === "Refered by Trustee";
	frm.toggle_display("referred_by_trustee", is_referred_by_trustee);
	frm.toggle_reqd("referred_by_trustee", is_referred_by_trustee);
	frm.toggle_display("parent_donor", !is_referred_by_trustee);
}

function add_donor_tree_button(frm) {
	frm.add_custom_button(
		__("Donations Tree"),
		() => frappe.set_route("Tree", "Donor"),
		__("Tree Views")
	);
}

function set_value_if_changed(frm, fieldname, value) {
	const current_value = frm.doc[fieldname] || "";
	const new_value = value || "";

	if (String(current_value) !== String(new_value)) {
		frm.set_value(fieldname, value);
	}
}
