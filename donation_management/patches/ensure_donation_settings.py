import frappe


def execute():
	if frappe.db.exists("DocType", "Donation Settings") and not frappe.db.exists(
		"Donation Settings", "Donation Settings"
	):
		frappe.get_doc({"doctype": "Donation Settings"}).insert(ignore_permissions=True)
