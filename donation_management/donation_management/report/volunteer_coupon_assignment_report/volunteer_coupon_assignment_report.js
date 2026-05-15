frappe.query_reports["Volunteer Coupon Assignment Report"] = {
	filters: [
		{
			fieldname: "volunteer_name",
			label: __("Volunteer"),
			fieldtype: "Link",
			options: "Employee",
		},
		{
			fieldname: "coupon_type",
			label: __("Coupon Type"),
			fieldtype: "Select",
			options: "\nZakat\nAtiya\nFitra\nSadqa",
		},
	],
};
