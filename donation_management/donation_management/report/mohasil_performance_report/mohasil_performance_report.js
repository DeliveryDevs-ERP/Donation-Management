// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.query_reports["Mohasil Performance Report"] = {
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
			fieldname: "mohasil",
			label: __("Mohasil"),
			fieldtype: "Link",
			options: "Employee",
			get_query: () => ({
				filters: {
					status: "Active",
					designation: "Mohasil",
				},
			}),
		},
		{
			fieldname: "donation_type",
			label: __("Donation Type"),
			fieldtype: "Select",
			options: "\nZakat\nAtiya\nSadqa\nFitra",
		},
		{
			fieldname: "source",
			label: __("Source"),
			fieldtype: "Select",
			options: "All\nDonation Order\nBox Collection",
			default: "All",
		},
		{
			fieldname: "commission_percentage",
			label: __("Commission Percentage"),
			fieldtype: "Float",
			default: 0,
		},
	],
};
