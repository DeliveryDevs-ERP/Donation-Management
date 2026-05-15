import frappe


def execute():
	for old_value in ("Walk-in Donor", "Trustee", "Existing Trustee"):
		frappe.db.set_value(
			"Donor",
			{"customer_type": old_value},
			"customer_type",
			"Walk-in",
			update_modified=False,
		)

	if frappe.db.has_column("Donor", "referred_by_trustee"):
		for donor in frappe.get_all("Donor", fields=["name", "customer_type", "referred_by_trustee"]):
			if donor.customer_type == "Walk-in" and donor.referred_by_trustee:
				frappe.db.set_value("Donor", donor.name, "referred_by_trustee", None, update_modified=False)
			elif donor.referred_by_trustee and not frappe.db.exists("Trustee", donor.referred_by_trustee):
				frappe.db.set_value("Donor", donor.name, "referred_by_trustee", None, update_modified=False)
