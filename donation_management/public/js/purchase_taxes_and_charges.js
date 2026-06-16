frappe.ui.form.on("Purchase Taxes and Charges", {
	rate(frm, cdt, cdn) {
		force_purchase_tax_deduction(frm, cdt, cdn);
	},

	add_deduct_tax(frm, cdt, cdn) {
		force_purchase_tax_deduction(frm, cdt, cdn);
	},
});

function force_purchase_tax_deduction(frm, cdt, cdn) {
	const row = locals[cdt]?.[cdn];
	if (!row || flt(row.rate) === 0 || row.add_deduct_tax === "Deduct") {
		return;
	}

	frappe.model.set_value(cdt, cdn, "add_deduct_tax", "Deduct");
}
