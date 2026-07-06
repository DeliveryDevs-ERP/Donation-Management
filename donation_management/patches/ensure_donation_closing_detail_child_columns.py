import frappe
from frappe.database.schema import add_column


def execute():
	if not frappe.db.table_exists("Donation Closing Detail"):
		return

	for fieldname in ("parent", "parentfield", "parenttype"):
		if not frappe.db.has_column("Donation Closing Detail", fieldname):
			add_column("Donation Closing Detail", fieldname, "Data")

	if not frappe.db.get_column_index(
		"tabDonation Closing Detail", "parent", unique=False
	):
		frappe.db.add_index("Donation Closing Detail", ["parent"])
