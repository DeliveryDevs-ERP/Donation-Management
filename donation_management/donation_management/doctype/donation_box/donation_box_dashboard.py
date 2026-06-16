from frappe import _


def get_data():
	return {
		"fieldname": "donation_box",
		"non_standard_fieldnames": {
			"Box Collection": "box_number",
		},
		"transactions": [
			{"label": _("Collection"), "items": ["Box Collection", "Box Collection Log"]},
		],
	}
