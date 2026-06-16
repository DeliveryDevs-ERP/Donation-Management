from frappe import _


def get_data():
	return {
		"fieldname": "donor",
		"non_standard_fieldnames": {
			"Donation Order": "donor_name",
		},
		"transactions": [
			{"label": _("Donations"), "items": ["Donation Order"]},
		],
	}
