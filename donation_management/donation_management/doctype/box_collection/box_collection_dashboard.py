from frappe import _


def get_data():
	return {
		"fieldname": "box_collection",
		"internal_links": {
			"Journal Entry": "journal_entry",
		},
		"transactions": [
			{"label": _("History"), "items": ["Box Collection Log"]},
			{"label": _("Accounting"), "items": ["Journal Entry"]},
		],
	}
