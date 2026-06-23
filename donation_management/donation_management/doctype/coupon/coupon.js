// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Coupon", {
	setup(frm) {
		frm.set_query("coupon_book", () => ({
			query: "donation_management.donation_management.doctype.coupon.coupon.get_available_coupon_books",
		}));
	},

	refresh(frm) {
		if (frm.doc.coupon_book) {
			set_coupon_book_details(frm);
		}
	},

	coupon_book(frm) {
		set_coupon_book_details(frm);
	},

	number_of_pages(frm) {
		set_coupon_amount(frm);
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
			"volunteer_area",
			"warehouse",
			"remaining_pages",
			"coupon_value",
			"status",
		])
		.then((response) => {
			const coupon_book = response.message || {};
			if (frm.is_new() && (coupon_book.status !== "Issued" || cint(coupon_book.remaining_pages) <= 0)) {
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
				frm.set_value("area", "");
				frm.set_value("warehouse", "");
				return;
			}

			frm.set_value("coupon_color", coupon_book.coupon_color || "");
			frm.set_value("volunteer_name", coupon_book.volunteer_name || "");
			frm.set_value("area", coupon_book.volunteer_area || "");
			frm.set_value("warehouse", coupon_book.warehouse || "");
			frm.__coupon_value = cint(coupon_book.coupon_value);
			if (!cint(frm.doc.number_of_pages)) {
				frm.set_value("number_of_pages", 1);
			}
			set_coupon_amount(frm);
		});
}

function set_coupon_amount(frm) {
	const coupon_value = cint(frm.__coupon_value);
	if (!coupon_value) {
		return;
	}

	frm.set_value("amount", cint(frm.doc.number_of_pages) * coupon_value);
}
