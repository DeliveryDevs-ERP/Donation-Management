import frappe


def execute():
	if frappe.db.exists("Donor", {"customer_name": "One Muslim"}):
		return

	donor = frappe.get_doc(
		{
			"doctype": "Donor",
			"naming_series": "DONOR-.YYYY.-",
			"customer_name": "One Muslim",
			"customer_type": "Walk-in",
			"is_group": 0,
		}
	)
	donor.insert(ignore_permissions=True)
