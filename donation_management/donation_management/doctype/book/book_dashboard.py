from frappe import _


def get_data():
	return {
		"fieldname": "book",
		"internal_links": {
			"Journal Entry": "journal_entry",
		},
		"transactions": [
			{"label": _("Coupons"), "items": ["Coupon"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
