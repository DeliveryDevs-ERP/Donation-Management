// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

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
			if (frm.doc.donation_type) {
				filters.account_name = ["like", `%${frm.doc.donation_type}%`];
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

			if (frm.doc.mode_of_payment_type === "Bank" && frm.doc.donation_type) {
				filters.account_name = ["like", `%${frm.doc.donation_type}%`];
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

			return { filters };
		});

		frm.set_query("student", "sponsorship_students", (doc, cdt, cdn) => {
			const selected_students = get_selected_sponsorship_students(doc, cdn);
			if (!selected_students.length) {
				return {};
			}

			return {
				filters: [["Student", "name", "not in", selected_students]],
			};
		});
	},

	refresh(frm) {
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
		update_accounting_fields(frm, true);
	},

	mode_of_payment(frm) {
		set_value_if_changed(frm, "mode_of_payment_type", "");
		set_value_if_changed(frm, "bank_account", "");
		set_value_if_changed(frm, "debit_account", "");
		update_accounting_fields(frm, true);
	},

	bank_account(frm) {
		if (frm.doc.mode_of_payment_type === "Bank") {
			set_value_if_changed(frm, "debit_account", frm.doc.bank_account || "");
		}
	},

	donation_type(frm) {
		if (frm.doc.mode_of_payment_type === "Bank") {
			set_value_if_changed(frm, "bank_account", "");
			set_value_if_changed(frm, "debit_account", "");
		}
		set_value_if_changed(frm, "credit_account", "");
		set_value_if_changed(frm, "accounting_cost_center", "");
		update_accounting_fields(frm, frm.doc.mode_of_payment_type === "Bank");
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

	sponsorship_students_add(frm) {
		apply_sponsorship_table_rules(frm);
		set_student_sponsorship_quantities(frm);
		set_sponsorship_totals(frm);
	},

	sponsorship_students_remove(frm) {
		set_sponsorship_totals(frm);
	},

	sponsorship_prisoners_add(frm) {
		apply_sponsorship_table_rules(frm);
		set_sponsorship_totals(frm);
	},

	sponsorship_prisoners_remove(frm) {
		set_sponsorship_totals(frm);
	},
});

frappe.ui.form.on("Donation Order Sponsorship Allocation", {
	student(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.parentfield !== "sponsorship_students") {
			return;
		}

		if (row.student && is_duplicate_sponsorship_student(frm, row.student, cdn)) {
			frappe.msgprint(__("Student {0} is already selected in this Donation Order.", [row.student]));
			set_child_value_if_changed(cdt, cdn, "student", "");
			return;
		}
	},

	quantity(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.parentfield === "sponsorship_students") {
			set_child_value_if_changed(cdt, cdn, "quantity", 1);
			set_sponsorship_row_totals(frm, cdt, cdn, "sponsorship_students", 1);
			return;
		}

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

			if (details.mode_of_payment_type === "Bank") {
				if (overwrite_debit_account || !frm.doc.bank_account) {
					set_value_if_changed(frm, "bank_account", details.debit_account || "");
				}
				set_value_if_changed(frm, "debit_account", frm.doc.bank_account || details.debit_account || "");
			} else {
				set_value_if_changed(frm, "bank_account", "");
				if (overwrite_debit_account || !frm.doc.debit_account) {
					set_value_if_changed(frm, "debit_account", details.debit_account || "");
				}
			}

			set_value_if_changed(frm, "credit_account", details.credit_account || "");
			set_value_if_changed(frm, "accounting_cost_center", details.cost_center || "");
		},
	});
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
	const show_student_sponsorship = is_sponsorship && has_donation_purpose && requires_student;
	const show_prisoner_sponsorship = is_sponsorship && has_donation_purpose && requires_prisoner;

	frm.toggle_display("beneficiary_section", requires_student || requires_prisoner);
	frm.toggle_display("student_name", requires_student && !is_sponsorship);
	frm.toggle_reqd("student_name", requires_student && !is_sponsorship);
	frm.toggle_display("student_mode", requires_student && frm.doc.student_mode && !is_sponsorship);
	frm.toggle_display("prisoner_name", requires_prisoner && !is_sponsorship);
	frm.toggle_reqd("prisoner_name", requires_prisoner && !is_sponsorship);
	frm.toggle_display("sponsorship_section", show_student_sponsorship || show_prisoner_sponsorship);
	frm.toggle_display("sponsorship_students", show_student_sponsorship);
	frm.toggle_display("sponsorship_prisoners", show_prisoner_sponsorship);
	apply_sponsorship_table_rules(frm);

	if (clear_hidden_values && (!requires_student || is_sponsorship)) {
		set_value_if_changed(frm, "student_name", "");
		set_value_if_changed(frm, "total_donation", 0);
	}

	if (clear_hidden_values && (!requires_prisoner || is_sponsorship)) {
		set_value_if_changed(frm, "prisoner_name", "");
	}

	if (clear_hidden_values && !show_student_sponsorship) {
		frm.clear_table("sponsorship_students");
		frm.refresh_field("sponsorship_students");
	}

	if (clear_hidden_values && !show_prisoner_sponsorship) {
		frm.clear_table("sponsorship_prisoners");
		frm.refresh_field("sponsorship_prisoners");
	}

	set_sponsorship_totals(frm);
}

function apply_sponsorship_table_rules(frm) {
	const show_student_sponsorship =
		frm.doc.purpose_of_donation === "Sponsorship"
		&& Boolean(frm.doc.donation_purpose)
		&& cint(frm.doc.requires_student);
	const show_prisoner_sponsorship =
		frm.doc.purpose_of_donation === "Sponsorship"
		&& Boolean(frm.doc.donation_purpose)
		&& cint(frm.doc.requires_prisoner);

	if (show_student_sponsorship) {
		set_student_sponsorship_quantities(frm);
		configure_sponsorship_grid(frm, "sponsorship_students", {
			student: { visible: true, reqd: true, read_only: false },
			quantity: { visible: false, reqd: false, read_only: true },
		});
		return;
	}

	if (show_prisoner_sponsorship) {
		clear_prisoner_sponsorship_students(frm);
		configure_sponsorship_grid(frm, "sponsorship_prisoners", {
			student: { visible: false, reqd: false, read_only: true },
			quantity: { visible: true, reqd: true, read_only: false },
		});
	}
}

function configure_sponsorship_grid(frm, table_fieldname, field_rules) {
	const grid = frm.fields_dict[table_fieldname]?.grid;
	if (!grid) {
		return;
	}

	["student", "quantity"].forEach((fieldname) => {
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

function set_student_sponsorship_quantities(frm) {
	(frm.doc.sponsorship_students || []).forEach((row) => {
		if (cint(row.quantity) !== 1) {
			frappe.model.set_value(row.doctype, row.name, "quantity", 1);
		}
	});
}

function clear_prisoner_sponsorship_students(frm) {
	(frm.doc.sponsorship_prisoners || []).forEach((row) => {
		if (row.student) {
			frappe.model.set_value(row.doctype, row.name, "student", "");
		}
	});
}

function set_previous_sponsorship_balance(frm) {
	if (frm.doc.purpose_of_donation !== "Sponsorship" || !frm.doc.donor_name) {
		set_value_if_changed(frm, "previous_sponsorship_balance", 0);
		set_value_if_changed(frm, "previous_balance_used", 0);
		set_sponsorship_totals(frm);
		return;
	}

	frappe.call({
		method: "donation_management.donation_management.api.get_donor_previous_sponsorship_balance",
		args: {
			donor: frm.doc.donor_name,
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

function get_selected_sponsorship_students(doc, current_cdn) {
	return (doc.sponsorship_students || [])
		.filter((row) => row.name !== current_cdn && row.student)
		.map((row) => row.student);
}

function is_duplicate_sponsorship_student(frm, student, current_cdn) {
	return (frm.doc.sponsorship_students || []).some(
		(row) => row.name !== current_cdn && row.student === student
	);
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
	const covered_months = monthly_total ? Math.min(allocated_amount / monthly_total, duration_months) : 0;

	set_child_value_if_changed(cdt, cdn, "total_program_donation", total_program_donation);
	set_child_value_if_changed(cdt, cdn, "covered_months", covered_months);
	set_child_value_if_changed(cdt, cdn, "remaining_months", Math.max(duration_months - covered_months, 0));
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
	if (row.parentfield === "sponsorship_students") {
		return 1;
	}

	return cint(row.quantity);
}

function set_sponsorship_totals(frm) {
	if (frm.doc.purpose_of_donation !== "Sponsorship") {
		set_value_if_changed(frm, "previous_sponsorship_balance", 0);
		set_value_if_changed(frm, "previous_balance_used", 0);
		set_value_if_changed(frm, "available_allocation_amount", 0);
		set_value_if_changed(frm, "allocated_amount", 0);
		set_value_if_changed(frm, "unallocated_amount", 0);
		set_value_if_changed(frm, "allocation_status", "");
		set_value_if_changed(frm, "total_sponsored_beneficiaries", 0);
		set_value_if_changed(frm, "total_covered_months", 0);
		return;
	}

	const student_rows = frm.doc.sponsorship_students || [];
	const prisoner_rows = frm.doc.sponsorship_prisoners || [];
	const allocated_amount = [...student_rows, ...prisoner_rows].reduce(
		(total, row) => total + flt(row.allocated_amount),
		0
	);
	const total_sponsored_beneficiaries =
		student_rows.length + prisoner_rows.reduce((total, row) => total + cint(row.quantity), 0);
	const total_covered_months = [...student_rows, ...prisoner_rows].reduce(
		(total, row) => total + flt(row.covered_months),
		0
	);
	const available_allocation_amount = flt(frm.doc.donation_amount) + flt(frm.doc.previous_balance_used);

	set_value_if_changed(frm, "total_donation", flt(frm.doc.donation_amount));
	set_value_if_changed(frm, "available_allocation_amount", available_allocation_amount);
	set_value_if_changed(frm, "allocated_amount", allocated_amount);
	set_value_if_changed(frm, "unallocated_amount", available_allocation_amount - allocated_amount);
	set_value_if_changed(frm, "allocation_status", get_allocation_status(frm, allocated_amount));
	set_value_if_changed(frm, "total_sponsored_beneficiaries", total_sponsored_beneficiaries);
	set_value_if_changed(frm, "total_covered_months", total_covered_months);
}

function get_allocation_status(frm, allocated_amount) {
	const available_allocation_amount = flt(frm.doc.donation_amount) + flt(frm.doc.previous_balance_used);
	const unallocated_amount = available_allocation_amount - flt(allocated_amount);
	if (flt(allocated_amount) <= 0) {
		return "Unallocated";
	}

	if (unallocated_amount > 0) {
		return "Partially Allocated";
	}

	return "Fully Allocated";
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
