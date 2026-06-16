// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const sponsorship_days_in_month = 30;
const prisoner_program_suffix = " - Prisoner";
const allowed_sponsorship_purposes = [
	"Sponsorship - Prisoner",
	"Sponsorship - Student",
	"Sponsorship - MTC",
	"Sponsorship - Maktab",
];
const bank_draft_mode_of_payment = "Bank Draft";

frappe.ui.form.on("Donation Order", {
	setup(frm) {
		frm.set_query("donor_name", () => {
			return {};
		});

		frm.set_query("mode_of_payment", () => {
			return {
				filters: {
					enabled: 1,
				},
			};
		});

		frm.set_query("bank_account", () => {
			const filters = { is_group: 0, account_type: "Bank" };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

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

			if (is_bank_draft_mode(frm) && frm.doc.donation_type) {
				filters.account_name = ["like", `%${get_receiving_account_donation_type(frm.doc.donation_type)}%`];
			}

			return { filters };
		});

		frm.set_query("credit_account", () => {
			const filters = { is_group: 0, root_type: ["in", ["Income", "Liability", "Equity"]] };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("donation_purpose", () => {
			const filters = {
				is_group: 0,
			};

			if (frm.doc.purpose_of_donation) {
				filters.purpose_group = frm.doc.purpose_of_donation;
			}

			if (frm.doc.purpose_of_donation === "Sponsorship") {
				filters.name = ["in", allowed_sponsorship_purposes];
			}

			return { filters };
		});

		frm.set_query("donation_purpose", "purpose_details", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			const filters = { is_group: 0 };
			if (row.donation_category) {
				filters.purpose_group = row.donation_category;
			}
			if (row.donation_category === "Sponsorship") {
				filters.name = ["in", allowed_sponsorship_purposes];
			}
			return { filters };
		});

		frm.set_query("credit_account", "purpose_details", () => {
			const filters = { is_group: 0, root_type: ["in", ["Income", "Liability", "Equity"]] };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});

		frm.set_query("debit_account", "purpose_details", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			const filters = { is_group: 0 };
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			if (["Cash", "Bank"].includes(frm.doc.mode_of_payment_type)) {
				filters.account_type = frm.doc.mode_of_payment_type;
			}
			if (is_bank_draft_mode(frm) && row.donation_type) {
				filters.account_name = ["like", `%${get_receiving_account_donation_type(row.donation_type)}%`];
			}
			return { filters };
		});

		frm.set_query("sponsorship_program", "sponsorship_students", () => {
			const program_modes = get_sponsorship_program_modes(frm);
			if (program_modes.student && !program_modes.prisoner) {
				return { filters: [["Sponsorship Program", "name", "not like", `%${prisoner_program_suffix}`]] };
			}
			if (program_modes.prisoner && !program_modes.student) {
				return { filters: [["Sponsorship Program", "name", "like", `%${prisoner_program_suffix}`]] };
			}
			return {};
		});
	},

	refresh(frm) {
		add_donation_order_action_buttons(frm);
		hide_legacy_purpose_fields(frm);
		toggle_purpose_grid_debit_account(frm);
		toggle_parent_debit_account(frm);
		update_total_amount_from_purpose_details(frm);
		update_beneficiary_fields(frm, false);
		if (frm.is_new()) {
			set_previous_sponsorship_balance(frm);
			update_accounting_fields(frm);
		}
		apply_sponsorship_table_rules(frm);
		set_sponsorship_totals(frm);
	},

	company(frm) {
		set_value_if_changed(frm, "debit_account", "");
		set_value_if_changed(frm, "credit_account", "");
		set_value_if_changed(frm, "accounting_cost_center", "");
		refresh_all_purpose_rows(frm);
		update_accounting_fields(frm, true);
	},

	mode_of_payment(frm) {
		set_value_if_changed(frm, "mode_of_payment_type", "");
		set_value_if_changed(frm, "bank_account", "");
		set_value_if_changed(frm, "debit_account", "");
		if (frm.doc.mode_of_payment !== "Cheque") {
			set_value_if_changed(frm, "is_post_dated_cheque", 0);
			set_value_if_changed(frm, "cheque_number", "");
			set_value_if_changed(frm, "cheque_deposit_date", "");
		}
		clear_purpose_row_debit_accounts(frm);
		update_accounting_fields(frm, true);
	},

	bank_account(frm) {
		apply_deposit_account_to_purpose_rows(frm);
		toggle_parent_debit_account(frm);
	},

	debit_account(frm) {
		apply_parent_debit_account_to_purpose_rows(frm);
	},

	donation_type(frm) {
		set_value_if_changed(frm, "credit_account", "");
		set_value_if_changed(frm, "accounting_cost_center", "");
		if (is_bank_draft_mode(frm)) {
			set_value_if_changed(frm, "debit_account", "");
			clear_purpose_row_debit_accounts(frm);
		}
		set_previous_sponsorship_balance(frm);
		update_accounting_fields(frm);
	},

	donor_cnic(frm) {
		set_donor_from_cnic(frm);
	},

	donor_phone_number(frm) {
		set_donor_from_phone(frm);
	},

	donor_name(frm) {
		set_donor_details_from_name(frm);
	},

	purpose_of_donation(frm) {
		set_value_if_changed(frm, "donation_purpose", "");
		set_value_if_changed(frm, "purpose_path", "");
		set_value_if_changed(frm, "requires_student", 0);
		set_value_if_changed(frm, "requires_prisoner", 0);
		set_value_if_changed(frm, "student_mode", "");
		update_beneficiary_fields(frm, true);
		set_previous_sponsorship_balance(frm);
		set_sponsorship_totals(frm);
	},

	donation_purpose(frm) {
		if (!frm.doc.donation_purpose) {
			set_value_if_changed(frm, "credit_account", "");
			set_value_if_changed(frm, "accounting_cost_center", "");
			update_beneficiary_fields(frm, true);
			return;
		}

		frappe.db
			.get_value("Donation Purpose", frm.doc.donation_purpose, [
				"purpose_path",
				"requires_student",
				"requires_prisoner",
				"student_mode",
			])
			.then((response) => {
				const purpose = response.message || {};
				set_value_if_changed(frm, "purpose_path", purpose.purpose_path || "");
				set_value_if_changed(frm, "requires_student", purpose.requires_student || 0);
				set_value_if_changed(frm, "requires_prisoner", purpose.requires_prisoner || 0);
				set_value_if_changed(frm, "student_mode", purpose.student_mode || "");
				update_beneficiary_fields(frm, true);
				set_previous_sponsorship_balance(frm);
				set_sponsorship_totals(frm);
				update_accounting_fields(frm);
			});
	},

	student_name(frm) {
		set_student_total_donation(frm);
	},

	donation_amount(frm) {
		set_student_total_donation(frm);
		set_sponsorship_totals(frm);
	},

	purpose_details_add(frm) {
		sync_primary_purpose_fields(frm);
		update_total_amount_from_purpose_details(frm);
	},

	purpose_details_remove(frm) {
		sync_primary_purpose_fields(frm);
		update_total_amount_from_purpose_details(frm);
		set_sponsorship_totals(frm);
	},

	sponsorship_students_add(frm) {
		apply_sponsorship_table_rules(frm);
		set_sponsorship_totals(frm);
	},

	sponsorship_students_remove(frm) {
		set_sponsorship_totals(frm);
	},

});

frappe.ui.form.on("Donation Order Purpose Detail", {
	donation_type(frm, cdt, cdn) {
		if (!is_deposit_account_mode(frm)) {
			set_child_value_if_changed(cdt, cdn, "debit_account", "");
		}
		if (is_bank_draft_mode(frm)) {
			set_value_if_changed(frm, "debit_account", "");
		}
		update_purpose_row_details(frm, cdt, cdn);
	},

	donation_category(frm, cdt, cdn) {
		set_child_value_if_changed(cdt, cdn, "donation_purpose", "");
		set_child_value_if_changed(cdt, cdn, "purpose_path", "");
		if (!is_deposit_account_mode(frm)) {
			set_child_value_if_changed(cdt, cdn, "debit_account", "");
		}
		set_child_value_if_changed(cdt, cdn, "credit_account", "");
		set_child_value_if_changed(cdt, cdn, "cost_center", "");
		update_purpose_row_details(frm, cdt, cdn);
	},

	donation_purpose(frm, cdt, cdn) {
		update_purpose_row_details(frm, cdt, cdn);
	},

	amount(frm) {
		update_total_amount_from_purpose_details(frm);
		sync_primary_purpose_fields(frm);
		set_sponsorship_totals(frm);
	},

	debit_account(frm) {
		sync_primary_purpose_fields(frm);
	},
});

frappe.ui.form.on("Donation Order Sponsorship Allocation", {
	quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		set_sponsorship_row_totals(frm, cdt, cdn, row.parentfield, get_sponsorship_row_quantity(row));
	},

	allocated_amount(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		set_sponsorship_row_totals(frm, cdt, cdn, row.parentfield, get_sponsorship_row_quantity(row));
	},

	sponsorship_program(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		set_program_details(frm, cdt, cdn, row.parentfield, get_sponsorship_row_quantity(row));
	},
});

function set_donor_from_cnic(frm) {
	if (!frm.doc.donor_cnic) {
		return;
	}

	const cnic_digits = get_cnic_digits(frm.doc.donor_cnic);
	if (cnic_digits.length < 13) {
		return;
	}

	if (cnic_digits.length > 13) {
		frappe.msgprint(__("Donor CNIC cannot contain more than 13 digits."));
		set_value_if_changed(frm, "donor_name", "");
		set_value_if_changed(frm, "name_on_donation_slip", "");
		set_previous_sponsorship_balance(frm);
		return;
	}

	const formatted_cnic = format_cnic(cnic_digits);

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_by_cnic",
		args: {
			donor_cnic: formatted_cnic,
		},
		callback(response) {
			const donor = response.message || {};
			if (donor.invalid) {
				return;
			}

			if (!donor.name) {
				show_create_donor_message(frm, {
					donor_cnic: formatted_cnic,
					donor_phone_number: frm.doc.donor_phone_number,
				});
				set_value_if_changed(frm, "donor_name", "");
				set_value_if_changed(frm, "donor_phone_number", "");
				set_value_if_changed(frm, "referred_by_trustee", "");
				set_value_if_changed(frm, "name_on_donation_slip", "");
				set_previous_sponsorship_balance(frm);
				return;
			}

			set_value_if_changed(frm, "donor_cnic", donor.donor_cnic || frm.doc.donor_cnic);
			set_value_if_changed(frm, "donor_name", donor.name);
			set_value_if_changed(frm, "donor_phone_number", donor.donor_phone_number || "");
			set_value_if_changed(frm, "referred_by_trustee", donor.referred_by_trustee || "");
			if (!frm.doc.name_on_donation_slip) {
				set_value_if_changed(frm, "name_on_donation_slip", donor.donor_name || donor.name);
			}
			set_previous_sponsorship_balance(frm);
		},
	});
}

function update_accounting_fields(frm, overwrite_debit_account = false) {
	frappe.call({
		method: "donation_management.donation_management.api.get_donation_order_accounting_details",
		args: {
			company: frm.doc.company,
			donation_type: frm.doc.donation_type,
			donation_purpose: frm.doc.donation_purpose,
			mode_of_payment: frm.doc.mode_of_payment,
		},
		callback(response) {
			const details = response.message || {};
			if (!frm.doc.company && details.company) {
				set_value_if_changed(frm, "company", details.company);
			}

			if (!frm.doc.currency && details.currency) {
				set_value_if_changed(frm, "currency", details.currency);
			}

			set_value_if_changed(frm, "mode_of_payment_type", details.mode_of_payment_type || "");
			toggle_purpose_grid_debit_account(frm);
			toggle_parent_debit_account(frm);

			if (is_deposit_account_mode(frm)) {
				apply_deposit_account_to_purpose_rows(frm);
			} else {
				set_value_if_changed(frm, "bank_account", "");
				if (overwrite_debit_account || !frm.doc.debit_account) {
					set_value_if_changed(frm, "debit_account", details.debit_account || "");
				}
			}

			set_value_if_changed(frm, "credit_account", details.credit_account || "");
			set_value_if_changed(frm, "accounting_cost_center", details.cost_center || "");
			refresh_all_purpose_rows(frm);
		},
	});
}

function add_donation_order_action_buttons(frm) {
	if (frm.is_new() || !frm.doc.donor_name) {
		return;
	}

	const action_group = __("Action");

	frm.add_custom_button(__("History"), () => {
		frappe.set_route("List", "Donation Order", {
			donor_name: frm.doc.donor_name,
		});
	}, action_group);

	frm.add_custom_button(__("Open Customer"), () => {
		frappe.set_route("Form", "Donor", frm.doc.donor_name);
	}, action_group);

	frm.add_custom_button(__("Donor Last Slip"), () => {
		open_donor_last_slip(frm);
	}, action_group);

	frm.add_custom_button(__("Previous Donor Balance Summary"), () => {
		frappe.set_route("query-report", "Donor Balance Report", {
			donor: frm.doc.donor_name,
		});
	}, action_group);

	if (can_create_pdc_journal_entry(frm)) {
		frm.add_custom_button(__("Create Journal Entry"), () => {
			create_pdc_journal_entry(frm);
		}, action_group);
	}
}

function can_create_pdc_journal_entry(frm) {
	return (
		!frm.is_new() &&
		frm.doc.docstatus === 1 &&
		frm.doc.mode_of_payment === "Cheque" &&
		frm.doc.is_post_dated_cheque &&
		frm.doc.pdc_status === "Pending Deposit" &&
		!frm.doc.journal_entry
	);
}

function create_pdc_journal_entry(frm) {
	frappe.call({
		method: "donation_management.donation_management.doctype.donation_order.donation_order.create_pdc_journal_entry",
		args: {
			donation_order: frm.doc.name,
		},
		freeze: true,
		freeze_message: __("Creating Journal Entry..."),
		callback(response) {
			const result = response.message || {};
			frappe.msgprint(
				__("Journal Entry {0} created.", [
					result.journal_entry || "",
				])
			);
			frm.reload_doc();
		},
	});
}

function open_donor_last_slip(frm) {
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Donation Order",
			fields: ["name"],
			filters: [
				["donor_name", "=", frm.doc.donor_name],
				["name", "!=", frm.doc.name || ""],
				["docstatus", "!=", 2],
			],
			order_by: "donation_posting_date desc, creation desc",
			limit_page_length: 1,
		},
		callback(response) {
			const last_slip = (response.message || [])[0];
			if (!last_slip) {
				frappe.msgprint(__("No previous donation slip found for this donor."));
				return;
			}

			frappe.set_route("Form", "Donation Order", last_slip.name);
		},
	});
}

function hide_legacy_purpose_fields(frm) {
	["donation_type", "purpose_of_donation", "donation_purpose", "purpose_path"].forEach((fieldname) => {
		frm.toggle_display(fieldname, false);
	});
}

function toggle_purpose_grid_debit_account(frm) {
	const show_row_debit_account = Boolean(frm.doc.mode_of_payment_type) || is_deposit_account_mode(frm);
	const cash_mode = frm.doc.mode_of_payment_type === "Cash";
	const manual_bank_mode = is_manual_bank_mode(frm);
	const bank_draft_mode = is_bank_draft_mode(frm);
	const deposit_account_mode = is_deposit_account_mode(frm);
	const grid = frm.fields_dict.purpose_details && frm.fields_dict.purpose_details.grid;
	if (!grid) {
		return;
	}

	grid.update_docfield_property("debit_account", "hidden", show_row_debit_account ? 0 : 1);
	grid.update_docfield_property("debit_account", "reqd", show_row_debit_account ? 1 : 0);
	grid.update_docfield_property("debit_account", "read_only", cash_mode || (manual_bank_mode && !bank_draft_mode) || deposit_account_mode ? 1 : 0);
	frm.refresh_field("purpose_details");
}

function toggle_parent_debit_account(frm) {
	const cash_mode = frm.doc.mode_of_payment_type === "Cash";
	const manual_bank_mode = is_manual_bank_mode(frm);
	const bank_draft_mode = is_bank_draft_mode(frm);
	const deposit_account_mode = is_deposit_account_mode(frm);

	frm.toggle_display("debit_account", cash_mode || (manual_bank_mode && !bank_draft_mode) || deposit_account_mode);
	frm.set_df_property("debit_account", "read_only", deposit_account_mode ? 1 : 0);
	frm.toggle_reqd("debit_account", cash_mode || (manual_bank_mode && !bank_draft_mode));
}

function clear_purpose_row_debit_accounts(frm) {
	(frm.doc.purpose_details || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "debit_account", "");
	});
}

function apply_parent_debit_account_to_purpose_rows(frm) {
	if (frm.doc.mode_of_payment_type !== "Cash" && (!is_manual_bank_mode(frm) || is_bank_draft_mode(frm))) {
		return;
	}

	(frm.doc.purpose_details || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "debit_account", frm.doc.debit_account || "");
	});
}

function refresh_all_purpose_rows(frm) {
	(frm.doc.purpose_details || []).forEach((row) => {
		update_purpose_row_details(frm, row.doctype, row.name);
	});
}

function apply_deposit_account_to_purpose_rows(frm) {
	if (!is_deposit_account_mode(frm)) {
		return;
	}

	set_value_if_changed(frm, "debit_account", frm.doc.bank_account || "");
	(frm.doc.purpose_details || []).forEach((row) => {
		frappe.model.set_value(row.doctype, row.name, "debit_account", frm.doc.bank_account || "");
	});
}

function update_purpose_row_details(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row) {
		return;
	}

	if (!row.donation_type || !row.donation_purpose || !frm.doc.company) {
		sync_primary_purpose_fields(frm);
		return;
	}

	frappe.db
		.get_value("Donation Purpose", row.donation_purpose, [
			"purpose_path",
			"purpose_group",
			"requires_student",
			"requires_prisoner",
			"student_mode",
		])
		.then((purpose_response) => {
			const purpose = purpose_response.message || {};
			if (purpose.purpose_group && row.donation_category && purpose.purpose_group !== row.donation_category) {
				frappe.msgprint(
					__("Donation Purpose {0} belongs to {1}, not {2}.", [
						row.donation_purpose,
						purpose.purpose_group,
						row.donation_category,
					])
				);
				set_child_value_if_changed(cdt, cdn, "donation_purpose", "");
				return;
			}

			if (purpose.purpose_group && !row.donation_category) {
				set_child_value_if_changed(cdt, cdn, "donation_category", purpose.purpose_group);
			}
			set_child_value_if_changed(cdt, cdn, "purpose_path", purpose.purpose_path || "");

			frappe.call({
				method: "donation_management.donation_management.api.get_donation_order_accounting_details",
				args: {
					company: frm.doc.company,
					donation_type: row.donation_type,
					donation_purpose: row.donation_purpose,
					mode_of_payment: frm.doc.mode_of_payment,
				},
				callback(response) {
					const details = response.message || {};
					if (details.mode_of_payment_type === "Cash") {
						set_child_value_if_changed(cdt, cdn, "debit_account", details.debit_account || "");
					} else if (is_deposit_account_mode(frm)) {
						set_child_value_if_changed(cdt, cdn, "debit_account", frm.doc.bank_account || "");
					} else if (details.mode_of_payment_type === "Bank") {
						set_child_value_if_changed(cdt, cdn, "debit_account", frm.doc.debit_account || details.debit_account || "");
					} else if (details.mode_of_payment_type) {
						if (!row.debit_account) {
							set_child_value_if_changed(cdt, cdn, "debit_account", details.debit_account || "");
						}
					} else {
						set_child_value_if_changed(cdt, cdn, "debit_account", "");
					}
					set_child_value_if_changed(cdt, cdn, "credit_account", details.credit_account || "");
					set_child_value_if_changed(cdt, cdn, "cost_center", details.cost_center || "");
					sync_primary_purpose_fields(frm);
					update_beneficiary_fields(frm, true);
				},
			});
		});
}

function sync_primary_purpose_fields(frm) {
	const rows = frm.doc.purpose_details || [];
	const primary_row = rows.find((row) => row.donation_category === "Sponsorship") || rows[0] || {};
	set_value_if_changed(frm, "donation_type", primary_row.donation_type || "");
	set_value_if_changed(frm, "purpose_of_donation", primary_row.donation_category || "");
	set_value_if_changed(frm, "donation_purpose", primary_row.donation_purpose || "");
	set_value_if_changed(frm, "purpose_path", primary_row.purpose_path || "");
	set_value_if_changed(frm, "credit_account", primary_row.credit_account || "");
	set_value_if_changed(frm, "accounting_cost_center", primary_row.cost_center || "");
	set_previous_sponsorship_balance(frm);
}

function update_total_amount_from_purpose_details(frm) {
	const total_amount = (frm.doc.purpose_details || []).reduce((total, row) => total + flt(row.amount), 0);
	set_value_if_changed(frm, "donation_amount", total_amount);
}

function set_donor_from_phone(frm) {
	if (!frm.doc.donor_phone_number) {
		clear_donor_details(frm);
		return;
	}

	const phone_digits = get_phone_digits(frm.doc.donor_phone_number);
	if (phone_digits.length < 10) {
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_by_phone",
		args: {
			donor_phone_number: frm.doc.donor_phone_number,
		},
		callback(response) {
			const donor = response.message || {};
			if (donor.invalid) {
				return;
			}

			if (!donor.name) {
				show_create_donor_message(frm, {
					donor_cnic: frm.doc.donor_cnic,
					donor_phone_number: frm.doc.donor_phone_number,
				});
				set_value_if_changed(frm, "donor_name", "");
				set_value_if_changed(frm, "donor_cnic", "");
				set_value_if_changed(frm, "name_on_donation_slip", "");
				set_value_if_changed(frm, "referred_by_trustee", "");
				set_previous_sponsorship_balance(frm);
				return;
			}

			set_value_if_changed(frm, "donor_cnic", donor.donor_cnic || "");
			set_value_if_changed(frm, "donor_name", donor.name);
			set_value_if_changed(frm, "donor_phone_number", donor.donor_phone_number || frm.doc.donor_phone_number);
			set_value_if_changed(frm, "referred_by_trustee", donor.referred_by_trustee || "");
			if (!frm.doc.name_on_donation_slip) {
				set_value_if_changed(frm, "name_on_donation_slip", donor.donor_name || donor.name);
			}
			set_previous_sponsorship_balance(frm);
		},
	});
}

function clear_donor_details(frm) {
	set_value_if_changed(frm, "donor_name", "");
	set_value_if_changed(frm, "donor_cnic", "");
	set_value_if_changed(frm, "name_on_donation_slip", "");
	set_value_if_changed(frm, "referred_by_trustee", "");
	set_previous_sponsorship_balance(frm);
}

function get_cnic_digits(cnic) {
	return String(cnic || "").replace(/\D/g, "");
}

function get_phone_digits(phone_number) {
	return String(phone_number || "").replace(/\D/g, "");
}

function format_cnic(cnic_digits) {
	return `${cnic_digits.slice(0, 5)}-${cnic_digits.slice(5, 12)}-${cnic_digits.slice(12)}`;
}

function show_create_donor_message(frm, donor_details) {
	const donor_cnic = donor_details.donor_cnic || "";
	const donor_phone_number = donor_details.donor_phone_number || "";
	const identifier = donor_cnic || donor_phone_number;

	frappe.msgprint({
		title: __("Donor Not Found"),
		message: __("No Donor found for {0}. You can create a new Donor.", [identifier]),
		primary_action: {
			label: __("Create Donor"),
			action() {
				frappe.hide_msgprint();
				frappe.new_doc("Donor", {
					donor_cnic,
					customer_type: "Walk-in",
					customer_name: frm.doc.name_on_donation_slip || "",
					donor_phone_number,
				});
			},
		},
	});
}

function set_donor_details_from_name(frm) {
	if (!frm.doc.donor_name) {
		set_value_if_changed(frm, "referred_by_trustee", "");
		set_previous_sponsorship_balance(frm);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_details",
		args: {
			donor: frm.doc.donor_name,
		},
		callback(response) {
			const donor = response.message || {};
			set_value_if_changed(frm, "donor_cnic", donor.donor_cnic || "");
			set_value_if_changed(frm, "donor_phone_number", donor.donor_phone_number || "");
			set_value_if_changed(frm, "referred_by_trustee", donor.referred_by_trustee || "");
			if (!frm.doc.name_on_donation_slip && donor.donor_name) {
				set_value_if_changed(frm, "name_on_donation_slip", donor.donor_name);
			}
			set_previous_sponsorship_balance(frm);
		}
	});
}

function update_beneficiary_fields(frm, clear_hidden_values) {
	const requires_student = cint(frm.doc.requires_student);
	const requires_prisoner = cint(frm.doc.requires_prisoner);
	const is_sponsorship = frm.doc.purpose_of_donation === "Sponsorship";
	const has_donation_purpose = Boolean(frm.doc.donation_purpose);
	const show_sponsorship_allocation = is_sponsorship && has_donation_purpose;

	frm.toggle_display("beneficiary_section", requires_student || requires_prisoner);
	frm.toggle_display("student_name", requires_student && !is_sponsorship);
	frm.toggle_reqd("student_name", requires_student && !is_sponsorship);
	frm.toggle_display("student_mode", requires_student && frm.doc.student_mode && !is_sponsorship);
	frm.toggle_display("prisoner_name", requires_prisoner && !is_sponsorship);
	frm.toggle_reqd("prisoner_name", requires_prisoner && !is_sponsorship);
	frm.toggle_display("sponsorship_section", show_sponsorship_allocation);
	frm.toggle_display("sponsorship_students", show_sponsorship_allocation);
	apply_sponsorship_table_rules(frm);

	if (clear_hidden_values && (!requires_student || is_sponsorship)) {
		set_value_if_changed(frm, "student_name", "");
		set_value_if_changed(frm, "total_donation", 0);
	}

	if (clear_hidden_values && (!requires_prisoner || is_sponsorship)) {
		set_value_if_changed(frm, "prisoner_name", "");
	}

	if (clear_hidden_values && !show_sponsorship_allocation) {
		frm.clear_table("sponsorship_students");
		frm.refresh_field("sponsorship_students");
	}

	set_sponsorship_totals(frm);
}

function apply_sponsorship_table_rules(frm) {
	const show_sponsorship_allocation =
		frm.doc.purpose_of_donation === "Sponsorship"
		&& Boolean(frm.doc.donation_purpose);

	if (show_sponsorship_allocation) {
		configure_sponsorship_grid(frm, "sponsorship_students", {
			quantity: { visible: true, reqd: true, read_only: false },
		});
	}
}

function configure_sponsorship_grid(frm, table_fieldname, field_rules) {
	const grid = frm.fields_dict[table_fieldname]?.grid;
	if (!grid) {
		return;
	}

	["quantity"].forEach((fieldname) => {
		set_grid_field_property(grid, fieldname, "hidden", 0);
		set_grid_field_property(grid, fieldname, "read_only", 0);
		set_grid_field_property(grid, fieldname, "reqd", 0);
		grid.set_column_disp(fieldname, true);
	});

	Object.keys(field_rules).forEach((fieldname) => {
		const rule = field_rules[fieldname];
		set_grid_field_property(grid, fieldname, "hidden", rule.visible ? 0 : 1);
		set_grid_field_property(grid, fieldname, "read_only", rule.read_only ? 1 : 0);
		set_grid_field_property(grid, fieldname, "reqd", rule.reqd ? 1 : 0);
		grid.set_column_disp(fieldname, Boolean(rule.visible));
	});

	grid.refresh();
	frm.refresh_field(table_fieldname);
}

function set_grid_field_property(grid, fieldname, property, value) {
	if (grid.update_docfield_property) {
		grid.update_docfield_property(fieldname, property, value);
	}

	const docfield = (grid.docfields || []).find((field) => field.fieldname === fieldname);
	if (docfield) {
		docfield[property] = value;
	}
}

function set_previous_sponsorship_balance(frm) {
	if (frm.doc.purpose_of_donation !== "Sponsorship" || !frm.doc.donor_name || !frm.doc.donation_type) {
		set_value_if_changed(frm, "previous_sponsorship_balance", 0);
		set_value_if_changed(frm, "previous_balance_used", 0);
		set_sponsorship_totals(frm);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_previous_sponsorship_balance",
		args: {
			donor: frm.doc.donor_name,
			donation_type: frm.doc.donation_type,
			exclude_donation_order: frm.doc.name,
		},
		callback(response) {
			const previous_balance = flt(response.message);
			set_value_if_changed(frm, "previous_sponsorship_balance", previous_balance);
			set_value_if_changed(frm, "previous_balance_used", previous_balance);
			set_sponsorship_totals(frm);
		},
	});
}

function set_student_total_donation(frm) {
	if (frm.doc.purpose_of_donation === "Sponsorship" || !frm.doc.student_name) {
		set_value_if_changed(frm, "total_donation", 0);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_student_total_donation",
		args: {
			student_name: frm.doc.student_name,
			exclude_donation_order: frm.doc.name,
		},
		callback(response) {
			const previous_total = flt(response.message);
			set_value_if_changed(frm, "total_donation", previous_total + flt(frm.doc.donation_amount));
		},
	});
}

function set_program_details(frm, cdt, cdn, table_fieldname, quantity) {
	const row = locals[cdt][cdn];
	if (!row.sponsorship_program) {
		set_child_value_if_changed(cdt, cdn, "monthly_donation", 0);
		set_child_value_if_changed(cdt, cdn, "duration_months", 0);
		set_child_value_if_changed(cdt, cdn, "total_program_donation", 0);
		set_sponsorship_row_totals(frm, cdt, cdn, table_fieldname, quantity);
		return;
	}

	frappe.db
		.get_value("Sponsorship Program", row.sponsorship_program, [
			"monthly_donation",
			"duration_months",
			"total_program_donation",
		])
		.then((response) => {
			const program = response.message || {};
			set_child_value_if_changed(cdt, cdn, "monthly_donation", program.monthly_donation || 0);
			set_child_value_if_changed(cdt, cdn, "duration_months", program.duration_months || 0);
			set_child_value_if_changed(
				cdt,
				cdn,
				"total_program_donation",
				program.total_program_donation || 0
			);
			set_sponsorship_row_totals(frm, cdt, cdn, table_fieldname, quantity);
		});
}

function set_sponsorship_row_totals(frm, cdt, cdn, table_fieldname, quantity) {
	const row = locals[cdt][cdn];
	if (!row) {
		return;
	}

	quantity = cint(quantity) || 0;
	const monthly_donation = flt(row.monthly_donation);
	const duration_months = flt(row.duration_months);
	const allocated_amount = flt(row.allocated_amount);
	const total_program_donation = monthly_donation * duration_months * quantity;
	const monthly_total = monthly_donation * quantity;
	const total_days = Math.round(duration_months * sponsorship_days_in_month);
	const covered_days = monthly_total
		? Math.min(Math.round((allocated_amount / monthly_total) * sponsorship_days_in_month), total_days)
		: 0;
	const remaining_days = Math.max(total_days - covered_days, 0);
	const covered_months = covered_days / sponsorship_days_in_month;
	const remaining_months = remaining_days / sponsorship_days_in_month;

	set_child_value_if_changed(cdt, cdn, "total_program_donation", total_program_donation);
	set_child_value_if_changed(cdt, cdn, "covered_months", covered_months);
	set_child_value_if_changed(cdt, cdn, "covered_duration", format_sponsorship_duration(covered_days));
	set_child_value_if_changed(cdt, cdn, "remaining_months", remaining_months);
	set_child_value_if_changed(cdt, cdn, "remaining_duration", format_sponsorship_duration(remaining_days));
	set_child_value_if_changed(
		cdt,
		cdn,
		"remaining_amount",
		Math.max(total_program_donation - allocated_amount, 0)
	);

	frm.refresh_field(table_fieldname);
	set_sponsorship_totals(frm);
}

function get_sponsorship_row_quantity(row) {
	return cint(row.quantity);
}

function set_sponsorship_totals(frm) {
	if (frm.doc.purpose_of_donation !== "Sponsorship") {
		set_value_if_changed(frm, "previous_sponsorship_balance", 0);
		set_value_if_changed(frm, "previous_balance_used", 0);
		set_value_if_changed(frm, "sponsorship_amount", 0);
		set_value_if_changed(frm, "available_allocation_amount", 0);
		set_value_if_changed(frm, "allocated_amount", 0);
		set_value_if_changed(frm, "unallocated_amount", 0);
		set_value_if_changed(frm, "total_program_amount", 0);
		set_value_if_changed(frm, "remaining_program_cost", 0);
		set_value_if_changed(frm, "allocation_status", "");
		set_value_if_changed(frm, "sponsored_student_count", 0);
		set_value_if_changed(frm, "total_sponsored_beneficiaries", 0);
		set_value_if_changed(frm, "total_covered_months", 0);
		return;
	}

	const allocation_rows = frm.doc.sponsorship_students || [];
	const allocated_amount = allocation_rows.reduce(
		(total, row) => total + flt(row.allocated_amount),
		0
	);
	const total_program_amount = allocation_rows.reduce(
		(total, row) => total + flt(row.total_program_donation),
		0
	);
	const total_sponsored_beneficiaries = allocation_rows.reduce(
		(total, row) => total + cint(row.quantity),
		0
	);
	const total_covered_months = allocation_rows.reduce(
		(total, row) => total + flt(row.covered_months),
		0
	);
	const sponsorship_amount = get_sponsorship_purpose_amount(frm);
	const available_allocation_amount = sponsorship_amount + flt(frm.doc.previous_balance_used);

	set_value_if_changed(frm, "total_donation", flt(frm.doc.donation_amount));
	set_value_if_changed(frm, "sponsorship_amount", sponsorship_amount);
	set_value_if_changed(frm, "available_allocation_amount", available_allocation_amount);
	set_value_if_changed(frm, "allocated_amount", allocated_amount);
	set_value_if_changed(frm, "unallocated_amount", available_allocation_amount - allocated_amount);
	set_value_if_changed(frm, "total_program_amount", total_program_amount);
	set_value_if_changed(frm, "remaining_program_cost", Math.max(total_program_amount - allocated_amount, 0));
	set_value_if_changed(frm, "allocation_status", get_allocation_status(frm, allocated_amount));
	set_value_if_changed(frm, "sponsored_student_count", total_sponsored_beneficiaries);
	set_value_if_changed(frm, "total_sponsored_beneficiaries", total_sponsored_beneficiaries);
	set_value_if_changed(frm, "total_covered_months", total_covered_months);
}

function is_prisoner_sponsorship_program(program_name) {
	return Boolean(program_name && program_name.endsWith(prisoner_program_suffix));
}

function get_sponsorship_program_modes(frm) {
	const modes = {
		student: false,
		prisoner: false,
	};

	(frm.doc.purpose_details || []).forEach((row) => {
		if (row.donation_category !== "Sponsorship") {
			return;
		}

		if (row.donation_purpose === "Sponsorship - Prisoner") {
			modes.prisoner = true;
		} else {
			modes.student = true;
		}
	});

	return modes;
}

function format_sponsorship_duration(total_days) {
	total_days = Math.max(cint(total_days), 0);
	const months = Math.floor(total_days / sponsorship_days_in_month);
	const days = total_days % sponsorship_days_in_month;
	const parts = [];
	if (months) {
		parts.push(__("{0} month{1}", [months, months === 1 ? "" : "s"]));
	}
	if (days) {
		parts.push(__("{0} day{1}", [days, days === 1 ? "" : "s"]));
	}
	return parts.join(" ") || __("0 days");
}

function get_receiving_account_donation_type(donation_type) {
	return donation_type === "Zakat" ? "Zakat" : "Atiya";
}

function is_deposit_account_mode(frm) {
	return ["Cheque", "Card Payment"].includes(frm.doc.mode_of_payment);
}

function is_bank_draft_mode(frm) {
	return frm.doc.mode_of_payment === bank_draft_mode_of_payment;
}

function is_manual_bank_mode(frm) {
	return frm.doc.mode_of_payment_type === "Bank" && !is_deposit_account_mode(frm);
}

function get_allocation_status(frm, allocated_amount) {
	const available_allocation_amount = get_sponsorship_purpose_amount(frm) + flt(frm.doc.previous_balance_used);
	const unallocated_amount = available_allocation_amount - flt(allocated_amount);
	if (flt(allocated_amount) <= 0) {
		return "Unallocated";
	}

	if (unallocated_amount > 0) {
		return "Partially Allocated";
	}

	return "Fully Allocated";
}

function get_sponsorship_purpose_amount(frm) {
	return (frm.doc.purpose_details || [])
		.filter((row) => row.donation_category === "Sponsorship")
		.reduce((total, row) => total + flt(row.amount), 0);
}

function set_value_if_changed(frm, fieldname, value) {
	const current_value = frm.doc[fieldname] || "";
	const new_value = value || "";

	if (String(current_value) !== String(new_value)) {
		frm.set_value(fieldname, value);
	}
}

function set_child_value_if_changed(cdt, cdn, fieldname, value) {
	const row = locals[cdt][cdn];
	const current_value = row[fieldname] || "";
	const new_value = value || "";

	if (String(current_value) !== String(new_value)) {
		frappe.model.set_value(cdt, cdn, fieldname, value);
	}
}
