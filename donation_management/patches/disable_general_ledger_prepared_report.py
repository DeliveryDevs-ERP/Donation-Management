import frappe


def execute():
	if not frappe.db.exists("Report", "General Ledger"):
		return

	frappe.db.set_value("Report", "General Ledger", "prepared_report", 0, update_modified=False)
