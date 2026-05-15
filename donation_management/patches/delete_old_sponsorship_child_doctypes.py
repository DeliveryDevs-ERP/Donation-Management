import frappe


def execute():
	for doctype in (
		"Donation Order Sponsorship Student",
		"Donation Order Sponsorship Prisoner",
		"Donation Order Sponsorship Beneficiary",
	):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
