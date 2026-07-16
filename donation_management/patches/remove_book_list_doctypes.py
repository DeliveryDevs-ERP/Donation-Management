import frappe


def execute():
	for doctype in ("Book List", "Book List Detail"):
		if frappe.db.exists("DocType", doctype):
			frappe.delete_doc("DocType", doctype, force=1, ignore_permissions=True)
