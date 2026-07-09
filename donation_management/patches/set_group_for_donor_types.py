import frappe


GROUP_DONOR_TYPES = ("General Donor", "Key Donor", "Sub Key Donor")


def execute():
	if not frappe.db.table_exists("Donor"):
		return

	frappe.db.set_value(
		"Donor",
		{"customer_type": ["in", GROUP_DONOR_TYPES]},
		"is_group",
		1,
		update_modified=False,
	)
