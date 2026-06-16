// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Trustee", {
	setup(frm) {
		frm.set_query("parent_trustee", () => ({
			filters: {
				is_group: 1,
				name: ["!=", frm.doc.name || ""],
			},
		}));
	},
});
