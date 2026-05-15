// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sponsorship Program", {
	monthly_donation(frm) {
		set_total_program_donation(frm);
	},

	duration_months(frm) {
		set_total_program_donation(frm);
	},
});

function set_total_program_donation(frm) {
	frm.set_value(
		"total_program_donation",
		flt(frm.doc.monthly_donation) * flt(frm.doc.duration_months)
	);
}
