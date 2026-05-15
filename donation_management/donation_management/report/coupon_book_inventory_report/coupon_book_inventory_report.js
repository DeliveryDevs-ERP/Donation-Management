frappe.query_reports["Coupon Book Inventory Report"] = {
	filters: [
		{
			fieldname: "coupon_type",
			label: __("Coupon Type"),
			fieldtype: "Select",
			options: "\nZakat\nAtiya\nFitra\nSadqa",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
	],
};
