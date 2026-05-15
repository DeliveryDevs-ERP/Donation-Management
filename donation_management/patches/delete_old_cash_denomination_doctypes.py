import frappe


def execute():
	for doctype in ("Box Collection Cash Denomination", "Coupon Book Cash Denomination"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)
