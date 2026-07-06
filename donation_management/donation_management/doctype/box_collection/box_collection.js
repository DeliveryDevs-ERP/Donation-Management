// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

const denominations = [10, 20, 50, 100, 500, 1000, 5000];
const assignment_fields = [
	"donation_location",
	"location_type",
	"location_name",
	"donor_location",
	"contact",
	"care_of_trustee",
	"care_of_donor",
	"deployment_officer",
];
const always_locked_fields = [
	"box_number",
	"box_code",
	"donation_head",
	"box_shape",
	"status",
	"assignment_date",
	"collection_date",
	"collection_office",
	"collected_amount",
];

frappe.ui.form.on("Box Collection", {
	setup(frm) {
		frm.set_query("mode_of_payment", () => ({
			filters: {
				enabled: 1,
				type: "Cash",
			},
		}));

		frm.set_query("debit_account", () => {
			const filters = {
				is_group: 0,
				account_type: "Cash",
			};

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			return { filters };
		});

		frm.set_query("credit_account", () => {
			const filters = {
				is_group: 0,
				root_type: "Income",
			};
			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}
			return { filters };
		});
	},

	refresh(frm) {
		set_field_locks(frm);

		if (frm.is_new() || frm.doc.docstatus !== 1) {
			return;
		}

		if (["Available", "Collected"].includes(frm.doc.status)) {
			const label = frm.doc.status === "Collected" ? __("Reissuance") : __("Issuance");
			const method = frm.doc.status === "Collected" ? "set_reissuance_date" : "set_issuance_date";
			frm.add_custom_button(label, () => show_assignment_dialog(frm, label, method), __("Actions"));
		}

		if (frm.doc.status === "Issued") {
			frm.add_custom_button(__("Collection"), () => show_collection_dialog(frm), __("Actions"));
		}
	},
});

function set_field_locks(frm) {
	always_locked_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", 1);
	});

	const lock_assignment = frm.doc.docstatus === 1 && frm.doc.status === "Issued";
	assignment_fields.forEach((fieldname) => {
		frm.set_df_property(fieldname, "read_only", lock_assignment ? 1 : 0);
	});
}

function show_assignment_dialog(frm, title, method) {
	const dialog = new frappe.ui.Dialog({
		title,
		fields: [
			{
				fieldname: "donation_location",
				fieldtype: "Link",
				label: __("Donation Location"),
				options: "Donation Location",
				reqd: 1,
				default: frm.doc.donation_location,
			},
			{
				fieldname: "location_type",
				fieldtype: "Select",
				label: __("Location Type"),
				options: "\nHome\nOffice\nShop\nOther",
				default: frm.doc.location_type,
			},
			{
				fieldname: "location_name",
				fieldtype: "Data",
				label: __("Shop/House Name"),
				default: frm.doc.location_name,
			},
			{
				fieldname: "donor_location",
				fieldtype: "Data",
				label: __("Address for Box Delivery"),
				default: frm.doc.donor_location,
			},
			{
				fieldname: "contact",
				fieldtype: "Data",
				label: __("Contact"),
				default: frm.doc.contact,
			},
			{
				fieldname: "care_of_trustee",
				fieldtype: "Link",
				label: __("Care Of Trustee"),
				options: "Trustee",
				default: frm.doc.care_of_trustee,
			},
			{
				fieldname: "care_of_donor",
				fieldtype: "Link",
				label: __("Care Of Donor"),
				options: "Donor",
				default: frm.doc.care_of_donor,
			},
			{
				fieldname: "deployment_officer",
				fieldtype: "Data",
				label: __("Delivery Staff"),
				reqd: 1,
				default: frm.doc.deployment_officer,
			},
		],
		primary_action_label: title,
		primary_action(values) {
			frm.call(method, values).then(() => {
				dialog.hide();
				frm.reload_doc();
			});
		},
	});

	dialog.show();
}

function show_collection_dialog(frm) {
	frappe.call({
		method: "donation_management.donation_management.api.get_collection_cash_accounting_defaults",
		args: {
			source_type: "Box Collection",
			donation_type: frm.doc.donation_head,
		},
		callback(response) {
			build_collection_dialog(frm, response.message || {});
		},
	});
}

function build_collection_dialog(frm, accounting_defaults) {
	const fields = [
		{
			fieldname: "collection_office",
			fieldtype: "Data",
			label: __("Collection Staff"),
			reqd: 1,
			default: frm.doc.collection_office,
		},
		{
			fieldname: "collected_amount",
			fieldtype: "Currency",
			label: __("Collected Amount"),
			reqd: 1,
			onchange: () => update_denomination_total(dialog),
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
			default: accounting_defaults.mode_of_payment || frm.doc.mode_of_payment,
			read_only: 1,
		},
		{
			fieldname: "debit_account",
			fieldtype: "Link",
			label: __("Debit Account"),
			options: "Account",
			reqd: 1,
			default: accounting_defaults.debit_account || frm.doc.debit_account,
			read_only: 1,
		},
		{
			fieldname: "credit_account",
			fieldtype: "Link",
			label: __("Income Account"),
			options: "Account",
			reqd: 1,
			default: frm.doc.credit_account || accounting_defaults.credit_account,
			get_query: () => {
				const filters = {
					is_group: 0,
					root_type: "Income",
				};
				const company = accounting_defaults.company || frm.doc.company;
				if (company) {
					filters.company = company;
				}
				return { filters };
			},
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
			onchange: () => update_denomination_total(dialog),
		});
	});

	fields.push({
		fieldname: "denomination_total",
		fieldtype: "Currency",
		label: __("Denomination Total"),
		read_only: 1,
	});

	const dialog = new frappe.ui.Dialog({
		title: __("Collection"),
		fields,
		primary_action_label: __("Collection"),
		primary_action(values) {
			if (!validate_denomination_total(dialog)) {
				return;
			}

			const denomination_values = {};
			denominations.forEach((denomination) => {
				denomination_values[denomination] = values[`denomination_${denomination}`] || 0;
			});

			frm.call("set_collection_date", {
				collection_office: values.collection_office,
				collected_amount: values.collected_amount,
				denominations: denomination_values,
				mode_of_payment: values.mode_of_payment,
				debit_account: values.debit_account,
				credit_account: values.credit_account,
			}).then(() => {
				dialog.hide();
				frm.reload_doc();
			});
		},
	});

	dialog.show();
	update_denomination_total(dialog);
}

function update_denomination_total(dialog) {
	let total = 0;
	denominations.forEach((denomination) => {
		total += denomination * flt(dialog.get_value(`denomination_${denomination}`));
	});
	dialog.set_value("denomination_total", total);
}

function validate_denomination_total(dialog) {
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
