// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Donation Source Account Mapping", {
	setup(frm) {
		frm.set_query("credit_account", () => {
			const filters = {
				is_group: 0,
				root_type: ["in", ["Income", "Liability", "Equity"]],
			};

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			return { filters };
		});

		frm.set_query("cost_center", () => {
			const filters = {
				is_group: 0,
			};

			if (frm.doc.company) {
				filters.company = frm.doc.company;
			}

			return { filters };
		});
	},
});
