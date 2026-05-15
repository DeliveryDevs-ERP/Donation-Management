// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Coupon", {
	setup(frm) {
		frm.set_query("coupon_book", () => ({
			filters: {
				status: "Issued",
				remaining_pages: [">", 0],
			},
		}));
	},

	coupon_book(frm) {
		set_coupon_book_details(frm);
	},
});

function set_coupon_book_details(frm) {
	if (!frm.doc.coupon_book) {
		return;
	}

	frappe.db
		.get_value("Coupon Book", frm.doc.coupon_book, [
			"coupon_type",
			"coupon_color",
			"volunteer_name",
			"warehouse",
			"remaining_pages",
		])
		.then((response) => {
			const coupon_book = response.message || {};
			if (cint(coupon_book.remaining_pages) <= 0) {
				frappe.msgprint({
					title: __("All Pages Used"),
					message: __("All pages are used for Coupon Book {0}. New Coupon cannot be created.", [
						frm.doc.coupon_book,
					]),
					indicator: "red",
				});
				frm.set_value("coupon_book", "");
				frm.set_value("coupon_color", "");
				frm.set_value("volunteer_name", "");
				frm.set_value("warehouse", "");
				return;
			}

			frm.set_value("coupon_color", coupon_book.coupon_color || "");
			frm.set_value("volunteer_name", coupon_book.volunteer_name || "");
			frm.set_value("warehouse", coupon_book.warehouse || "");
		});
}
