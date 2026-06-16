frappe.ui.form.on("Journal Entry", {
	setup(frm) {
		add_empty_voucher_type_option(frm);
	},

	refresh(frm) {
		add_empty_voucher_type_option(frm);
	},
});

function add_empty_voucher_type_option(frm) {
	const field = frm.get_field("voucher_type");
	if (!field?.df?.options) {
		return;
	}

	const options = String(field.df.options);
	if (options.startsWith("\n")) {
		return;
	}

	frm.set_df_property("voucher_type", "options", `\n${options}`);
}
