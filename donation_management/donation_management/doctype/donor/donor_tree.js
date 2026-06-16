frappe.treeview_settings["Donor"] = {
	breadcrumb: "Donation Management",
	title: __("Donations"),
	root_label: "Donations",
	get_tree_root: false,
	disable_add_node: true,
	get_tree_nodes:
		"donation_management.donation_management.doctype.donor.donor.get_referral_tree_children",
	get_label(node) {
		return __(node.title || node.label);
	},
	toolbar: [
		{
			label: __("Open"),
			condition(node) {
				return (
					!node.is_root &&
					!node.data.hide_open &&
					node.data.reference_doctype &&
					node.data.reference_name
				);
			},
			click(node) {
				frappe.set_route("Form", node.data.reference_doctype, node.data.reference_name);
			},
		},
	],
};
