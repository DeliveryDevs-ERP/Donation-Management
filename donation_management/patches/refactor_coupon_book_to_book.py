import frappe


def execute():
	delete_coupon_related_transaction_data()
	rename_doctype_if_needed("Coupon Book", "Book")
	rename_doctype_if_needed("Coupon Book Page Adjustment", "Book Page Adjustment")
	rename_doctype_if_needed("Coupon Book Inventory", "Book Inventory")
	delete_old_report_if_needed()
	update_source_type_values()


def delete_coupon_related_transaction_data():
	delete_rows("Donation Closing Detail", {"source_doctype": ["in", ("Coupon Book", "Book")]})
	delete_table_rows("Coupon")
	delete_table_rows("Coupon Book Page Adjustment")
	delete_table_rows("Book Page Adjustment")
	delete_table_rows("Coupon Book Inventory")
	delete_table_rows("Book Inventory")
	delete_table_rows("Coupon Book")
	delete_table_rows("Book")


def delete_rows(doctype, filters):
	if not frappe.db.table_exists(doctype):
		return
	for name in frappe.get_all(doctype, filters=filters, pluck="name"):
		frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)


def delete_table_rows(doctype):
	if frappe.db.table_exists(doctype):
		frappe.db.sql("delete from `tab{0}`".format(doctype.replace("`", "")))


def rename_doctype_if_needed(old_name, new_name):
	if frappe.db.exists("DocType", new_name):
		if frappe.db.exists("DocType", old_name):
			frappe.delete_doc("DocType", old_name, force=1, ignore_permissions=True)
		return

	if frappe.db.exists("DocType", old_name):
		frappe.rename_doc("DocType", old_name, new_name, force=True)


def delete_old_report_if_needed():
	if frappe.db.exists("Report", "Coupon Book Inventory Report"):
		frappe.delete_doc("Report", "Coupon Book Inventory Report", force=1, ignore_permissions=True)


def update_source_type_values():
	if frappe.db.table_exists("Donation Source Account Mapping"):
		frappe.db.sql(
			"""
			update `tabDonation Source Account Mapping`
			set source_type = 'Book'
			where source_type = 'Coupon Book'
			"""
		)

	if frappe.db.table_exists("Donation Closing Detail"):
		frappe.db.sql(
			"""
			update `tabDonation Closing Detail`
			set source_doctype = 'Book'
			where source_doctype = 'Coupon Book'
			"""
		)
