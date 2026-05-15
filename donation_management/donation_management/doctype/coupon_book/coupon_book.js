// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const coupon_colors = {
	Zakat: "Green",
	Atiya: "Blue",
	Fitra: "Purple",
	Sadqa: "Orange",
};
const denominations = [10, 20, 50, 100, 500, 1000, 5000];

frappe.ui.form.on("Coupon Book", {
	setup(frm) {
		frm.set_query("mode_of_payment", () => ({
			filters: {
				enabled: 1,
			},
		}));

		frm.set_query("debit_account", () => {
			const filters = {
				is_group: 0,
			};

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			if (["Cash", "Bank"].includes(frm.doc.mode_of_payment_type)) {
				filters.account_type = frm.doc.mode_of_payment_type;
			}

			if (frm.doc.mode_of_payment_type === "Bank" && frm.doc.coupon_type) {
				filters.account_name = ["like", `%${frm.doc.coupon_type}%`];
			}

			return { filters };
		});
	},

	refresh(frm) {
		set_collection_visibility(frm);
		add_action_buttons(frm);
	},

	coupon_type(frm) {
		set_coupon_color(frm);
		check_available_stock(frm);
	},

	warehouse(frm) {
		check_available_stock(frm);
	},

	status(frm) {
		set_collection_visibility(frm);
	},

	start_date(frm) {
		set_expiry_date(frm);
	},

	total_pages(frm) {
		set_remaining_pages(frm);
	},

	used_pages(frm) {
		set_remaining_pages(frm);
	},

	cash_denominations_add(frm) {
		update_denomination_rows(frm);
	},

	cash_denominations_remove(frm) {
		update_denomination_rows(frm);
	},
});

frappe.ui.form.on("Cash Denomination", {
	denomination(frm, cdt, cdn) {
		update_denomination_row(frm, cdt, cdn);
	},

	note_count(frm, cdt, cdn) {
		update_denomination_row(frm, cdt, cdn);
	},
});

function set_coupon_color(frm) {
	frm.set_value("coupon_color", coupon_colors[frm.doc.coupon_type] || "");
}

function check_available_stock(frm) {
	if (!frm.doc.coupon_type || !frm.doc.warehouse || frm.doc.status) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.doctype.coupon_book.coupon_book.get_available_coupon_book_stock",
		args: {
			coupon_type: frm.doc.coupon_type,
			warehouse: frm.doc.warehouse,
		},
		callback(response) {
			const available_stock = cint(response.message);
			if (available_stock <= 0) {
				frappe.msgprint(
					__("No Coupon Book stock is available for {0} in warehouse {1}.", [
						frm.doc.coupon_type,
						frm.doc.warehouse,
					])
				);
				return;
			}

			frappe.show_alert({
				message: __("Available Coupon Book stock: {0}", [available_stock]),
				indicator: "green",
			});
		},
	});
}

function set_expiry_date(frm) {
	if (!frm.doc.start_date) {
		frm.set_value("expiry_date", "");
		return;
	}

	frm.set_value("expiry_date", frappe.datetime.add_days(frm.doc.start_date, 45));
}

function set_remaining_pages(frm) {
	const remaining_pages = cint(frm.doc.total_pages) - cint(frm.doc.used_pages);
	frm.set_value("remaining_pages", remaining_pages);
}

function update_denomination_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "amount", cint(row.denomination) * cint(row.note_count));
	update_denomination_rows(frm);
}

function update_denomination_rows(frm) {
	let total = 0;
	(frm.doc.cash_denominations || []).forEach((row) => {
		total += flt(row.amount);
	});
	frm.set_value("collected_amount", total);
}

function set_collection_visibility(frm) {
	const show_collection = ["Returned", "Closed"].includes(frm.doc.status);
	frm.toggle_display("collection_section", show_collection);
	frm.toggle_reqd("collected_amount", show_collection);
	frm.toggle_reqd("cash_denominations", show_collection);
	frm.set_df_property("status", "read_only", 1);
}

function add_action_buttons(frm) {
	if (frm.is_new()) {
		return;
	}

	if (!frm.doc.status) {
		frm.add_custom_button(__("Issue"), () => issue_coupon_book(frm), __("Actions"));
	} else if (frm.doc.status === "Issued") {
		frm.add_custom_button(__("Return"), () => show_return_dialog(frm), __("Actions"));
	} else if (frm.doc.status === "Returned") {
		frm.add_custom_button(__("Close"), () => close_coupon_book(frm), __("Actions"));
	}
}

function issue_coupon_book(frm) {
	frappe.call({
		method: "donation_management.donation_management.doctype.coupon_book.coupon_book.issue_coupon_book",
		args: {
			coupon_book: frm.doc.name,
		},
		freeze: true,
		callback() {
			frm.reload_doc();
		},
	});
}

function show_return_dialog(frm) {
	const fields = [
		{
			fieldname: "collected_amount",
			fieldtype: "Currency",
			label: __("Collected Amount"),
			reqd: 1,
			onchange: () => update_return_denomination_total(dialog),
		},
		{
			fieldname: "accounting_section",
			fieldtype: "Section Break",
			label: __("Accounting"),
		},
		{
			fieldname: "mode_of_payment",
			fieldtype: "Link",
			label: __("Mode of Payment"),
			options: "Mode of Payment",
			reqd: 1,
			default: frm.doc.mode_of_payment,
			onchange: () => update_dialog_accounting_fields(dialog, "Coupon Book", frm.doc.coupon_type),
		},
		{
			fieldname: "debit_account",
			fieldtype: "Link",
			label: __("Debit Account"),
			options: "Account",
			reqd: 1,
			default: frm.doc.debit_account,
			get_query: () => ({
				filters: {
					is_group: 0,
				},
			}),
		},
		{
			fieldname: "denomination_section",
			fieldtype: "Section Break",
			label: __("Cash Denominations"),
		},
	];

	denominations.forEach((denomination) => {
		fields.push({
			fieldname: `denomination_${denomination}`,
			fieldtype: "Int",
			label: __("{0} Rs Notes", [denomination]),
			default: 0,
			non_negative: 1,
			onchange: () => update_return_denomination_total(dialog),
		});
	});

	fields.push({
		fieldname: "denomination_total",
		fieldtype: "Currency",
		label: __("Denomination Total"),
		read_only: 1,
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Return Coupon Book"),
		fields,
		primary_action_label: __("Return"),
		primary_action(values) {
			if (!validate_return_denomination_total(dialog)) {
				return;
			}

			const denomination_rows = denominations.map((denomination) => ({
				denomination,
				note_count: cint(values[`denomination_${denomination}`]),
			}));

			frappe.call({
				method: "donation_management.donation_management.doctype.coupon_book.coupon_book.return_coupon_book",
				args: {
					coupon_book: frm.doc.name,
					collected_amount: values.collected_amount,
					denominations: denomination_rows,
					mode_of_payment: values.mode_of_payment,
					debit_account: values.debit_account,
				},
				freeze: true,
				callback() {
					dialog.hide();
					frm.reload_doc();
				},
			});
		},
	});

	dialog.show();
	update_return_denomination_total(dialog);
	update_dialog_accounting_fields(dialog, "Coupon Book", frm.doc.coupon_type);
}

function update_dialog_accounting_fields(dialog, source_type, donation_type) {
	const mode_of_payment = dialog.get_value("mode_of_payment");
	if (!mode_of_payment) {
		dialog.set_value("debit_account", "");
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_source_accounting_details",
		args: {
			source_type,
			donation_type,
			mode_of_payment,
		},
		callback(response) {
			const details = response.message || {};
			if (details.debit_account) {
				dialog.set_value("debit_account", details.debit_account);
			}
		},
	});
}

function update_return_denomination_total(dialog) {
	let total = 0;
	denominations.forEach((denomination) => {
		total += denomination * flt(dialog.get_value(`denomination_${denomination}`));
	});
	dialog.set_value("denomination_total", total);
}

function validate_return_denomination_total(dialog) {
	const collected_amount = flt(dialog.get_value("collected_amount"));
	const denomination_total = flt(dialog.get_value("denomination_total"));

	if (collected_amount !== denomination_total) {
		frappe.msgprint(
			__("Denomination total {0} must match Collected Amount {1}.", [
				format_currency(denomination_total),
				format_currency(collected_amount),
			])
		);
		return false;
	}

	return true;
}

function close_coupon_book(frm) {
	frappe.call({
		method: "donation_management.donation_management.doctype.coupon_book.coupon_book.close_coupon_book",
		args: {
			coupon_book: frm.doc.name,
		},
		freeze: true,
		callback() {
			frm.reload_doc();
		},
	});
}
