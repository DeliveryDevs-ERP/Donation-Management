import frappe


def execute():
	old_name = "Coupon Book Inventory Ledger"
	new_name = "Coupon Book Inventory"

	if frappe.db.exists("DocType", old_name) and not frappe.db.exists("DocType", new_name):
		frappe.rename_doc("DocType", old_name, new_name, force=True)
