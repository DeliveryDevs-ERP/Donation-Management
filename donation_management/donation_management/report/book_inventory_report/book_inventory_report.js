frappe.query_reports["Book Inventory Report"] = {
	filters: [
		{
			fieldname: "coupon_type",
			label: __("Coupon Type"),
			fieldtype: "Select",
			options: "\nZakat\nAtiya\nFitra\nFidya",
		},
		{
			fieldname: "warehouse",
			label: __("Warehouse"),
			fieldtype: "Link",
			options: "Warehouse",
		},
	],
};
