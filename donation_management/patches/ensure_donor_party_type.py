import frappe


def execute():
	if frappe.db.exists("Party Type", "Donor"):
		frappe.db.set_value("Party Type", "Donor", "account_type", "Cash", update_modified=False)
		return

	frappe.get_doc(
		{
			"doctype": "Party Type",
			"party_type": "Donor",
			"account_type": "Cash",
		}
	).insert(ignore_permissions=True)
