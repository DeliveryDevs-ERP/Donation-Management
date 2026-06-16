from frappe import _


def get_data():
	return {
		"fieldname": "donation_order",
		"internal_links": {
			"Journal Entry": "journal_entry",
		},
		"transactions": [
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
