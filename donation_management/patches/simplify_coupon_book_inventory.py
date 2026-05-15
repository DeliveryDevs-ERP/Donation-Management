import frappe


def execute():
	if frappe.db.table_exists("Coupon Book"):
		frappe.db.sql("update `tabCoupon Book` set status = '' where status = 'In Stock'")

	if not frappe.db.table_exists("Coupon Book Inventory"):
		return

	if frappe.db.has_column("Coupon Book Inventory", "movement_type") and frappe.db.has_column(
		"Coupon Book Inventory", "entry_type"
	):
		frappe.db.sql(
			"""
			update `tabCoupon Book Inventory`
			set movement_type = case
				when entry_type in ('Receipt', 'Issue', 'Return') then entry_type
				when coalesce(signed_quantity, 0) < 0 then 'Issue'
				else 'Receipt'
			end
			where coalesce(movement_type, '') = ''
			"""
		)

	if frappe.db.has_column("Coupon Book Inventory", "signed_quantity"):
		frappe.db.sql(
			"""
			update `tabCoupon Book Inventory`
			set signed_quantity = case
				when movement_type = 'Issue' then -abs(quantity)
				else abs(quantity)
			end
			where coalesce(signed_quantity, 0) = 0
			"""
		)
