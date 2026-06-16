from frappe import _


def get_data():
	return {
		"fieldname": "referred_by_trustee",
		"transactions": [
			{"label": _("Referrals"), "items": ["Donor", "Donation Order"]},
		],
	}
