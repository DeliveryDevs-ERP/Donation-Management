import frappe


def execute():
	delete_report("Book Inventory Report")
	delete_report("Coupon Book Inventory Report")
	delete_doctype("Book Inventory")
	delete_doctype("Coupon Book Inventory")
	delete_doctype("Coupon Book Inventory Ledger")


def delete_report(report_name):
	if frappe.db.exists("Report", report_name):
		frappe.delete_doc("Report", report_name, force=1, ignore_permissions=True)


def delete_doctype(doctype):
	if frappe.db.exists("DocType", doctype):
		frappe.delete_doc("DocType", doctype, force=1, ignore_permissions=True)
