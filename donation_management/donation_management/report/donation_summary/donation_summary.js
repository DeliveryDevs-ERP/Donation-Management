frappe.query_reports["Donation Summary"] = {
	filters: [
		{
			fieldname: "company",
			label: __("Company"),
			fieldtype: "Link",
			options: "Company",
			default: frappe.defaults.get_user_default("Company"),
			reqd: 1,
		},
		{
			fieldname: "from_date",
			label: __("From Date"),
			fieldtype: "Date",
			default: frappe.datetime.month_start(),
			reqd: 1,
		},
		{
			fieldname: "to_date",
			label: __("To Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{
			fieldname: "accounting_status",
			label: __("Accounting Status"),
			fieldtype: "Select",
			options: ["Posted", "Pending", "All"],
			default: "Posted",
			reqd: 1,
		},
	],

	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		if (data.is_section || data.is_total || data.is_summary) {
			value = `<strong>${value}</strong>`;
		}

		if (data.is_detail && column.fieldname === "summary_label") {
			value = `<span style="display:inline-block;padding-left:16px">${value}</span>`;
		}

		return value;
	},
};
