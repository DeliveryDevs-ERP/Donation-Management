from frappe import _


def get_data():
	return {
		"fieldname": "student",
		"non_standard_fieldnames": {
			"Donation Order": "student_name",
		},
		"transactions": [
			{"label": _("Donations"), "items": ["Donation Order"]},
		],
	}
