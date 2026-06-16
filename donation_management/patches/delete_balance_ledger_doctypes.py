import frappe


def execute():
	for report in ("Donor Balance Report",):
		if frappe.db.exists("Report", report):
			frappe.delete_doc("Report", report, force=True, ignore_permissions=True)

	for doctype in ("Donor Balance Ledger", "Sponsorship Balance Ledger"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
