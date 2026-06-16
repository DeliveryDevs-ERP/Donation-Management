frappe.ui.form.on("Additional Salary", {
	refresh(frm) {
		add_pause_buttons(frm);
		calculate_adjustment_amount(frm);
	},

	custom_adjustment_type(frm) {
		calculate_adjustment_amount(frm);
	},

	custom_overtime_hours(frm) {
		calculate_adjustment_amount(frm);
	},

	custom_overtime_rate(frm) {
		calculate_adjustment_amount(frm);
	},

	amount(frm) {
		calculate_balance(frm);
	},

	custom_total_adjustment_amount(frm) {
		calculate_balance(frm);
	},

	custom_paid_or_deducted_amount(frm) {
		calculate_balance(frm);
	},

	custom_paused(frm) {
		frm.set_value("disabled", frm.doc.custom_paused ? 1 : 0);
	},
});

function add_pause_buttons(frm) {
	if (frm.is_new()) {
		return;
	}

	const label = frm.doc.custom_paused || frm.doc.disabled ? __("Resume") : __("Pause");
	frm.add_custom_button(label, () => {
		const paused = frm.doc.custom_paused || frm.doc.disabled ? 0 : 1;
		frm.set_value("custom_paused", paused);
		frm.set_value("disabled", paused);
		frm.save();
	});
}

function calculate_adjustment_amount(frm) {
	if (frm.doc.custom_adjustment_type === "Overtime") {
		const hours = flt(frm.doc.custom_overtime_hours);
		const rate = flt(frm.doc.custom_overtime_rate);
		if (hours && rate) {
			frm.set_value("amount", hours * rate);
		}
	}
	calculate_balance(frm);
}

function calculate_balance(frm) {
	const total = flt(frm.doc.custom_total_adjustment_amount) || flt(frm.doc.amount);
	const paid = flt(frm.doc.custom_paid_or_deducted_amount);
	frm.set_value("custom_total_adjustment_amount", total);
	frm.set_value("custom_remaining_balance", Math.max(total - paid, 0));
}
