from frappe import _


def get_data(data=None):
	dashboard = {
		"fieldname": "donor_name",
		"transactions": [
			{"label": _("Donations"), "items": ["Donation Order"]},
		],
	}

	if data is None:
		return dashboard

	data["fieldname"] = dashboard["fieldname"]
	data.setdefault("transactions", [])

	for transaction in dashboard["transactions"]:
		for existing in data["transactions"]:
			if existing.get("label") == transaction.get("label"):
				for item in transaction["items"]:
					if item not in existing["items"]:
						existing["items"].append(item)
				break
		else:
			data["transactions"].append(transaction)

	return data
