// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const box_shapes = {
	Zakat: "Square",
	Atiya: "Triangle",
	Sadqa: "Trapezium",
};

frappe.ui.form.on("Donation Box", {
	box_number(frm) {
		set_box_code(frm);
	},

	donation_head(frm) {
		frm.set_value("box_shape", box_shapes[frm.doc.donation_head] || "");
		set_box_code(frm);
	},
});

function set_box_code(frm) {
	if (frm.doc.donation_head && frm.doc.box_number) {
		frm.set_value("box_code", `${frm.doc.donation_head}-${frm.doc.box_number}`);
	} else {
		frm.set_value("box_code", "");
	}
}
