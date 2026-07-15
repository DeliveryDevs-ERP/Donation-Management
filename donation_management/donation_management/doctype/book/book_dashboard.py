from frappe import _


def get_data():
	return {
		"fieldname": "book",
		"non_standard_fieldnames": {
			"Donation Order": "donation_book",
		},
		"internal_links": {
			"Journal Entry": "journal_entry",
		},
		"transactions": [
			{"label": _("Coupons"), "items": ["Coupon"]},
			{"label": _("Donation Orders"), "items": ["Donation Order"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
