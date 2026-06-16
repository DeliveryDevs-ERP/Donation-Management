import frappe


def execute():
	if not frappe.db.exists("Role", "CFO"):
		frappe.get_doc(
			{
				"doctype": "Role",
				"role_name": "CFO",
				"desk_access": 1,
			}
		).insert(ignore_permissions=True)
