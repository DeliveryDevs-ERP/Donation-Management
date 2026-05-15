import frappe
from frappe import _
from frappe.utils import cint


COUPON_TYPES = ("Zakat", "Atiya", "Fitra", "Sadqa")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Coupon Type"), "fieldname": "coupon_type", "fieldtype": "Data", "width": 130},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 180},
		{"label": _("Stock Added"), "fieldname": "stock_added", "fieldtype": "Int", "width": 120},
		{"label": _("Generated"), "fieldname": "generated", "fieldtype": "Int", "width": 110},
		{"label": _("Issued"), "fieldname": "issued", "fieldtype": "Int", "width": 110},
		{"label": _("Returned"), "fieldname": "returned", "fieldtype": "Int", "width": 110},
		{"label": _("Closed"), "fieldname": "closed", "fieldtype": "Int", "width": 110},
		{"label": _("Remaining"), "fieldname": "remaining", "fieldtype": "Int", "width": 120},
	]


def get_data(filters):
	conditions = {"docstatus": ["!=", 2]}
	if filters.get("coupon_type"):
		conditions["coupon_type"] = filters.coupon_type
	if filters.get("warehouse"):
		conditions["warehouse"] = filters.warehouse

	ledger_entries = frappe.get_all(
		"Coupon Book Inventory",
		filters=conditions,
		fields=["coupon_type", "warehouse", "movement_type", "quantity", "signed_quantity"],
	)

	coupon_books = frappe.get_all(
		"Coupon Book",
		filters=conditions,
		fields=["coupon_type", "warehouse", "status"],
	)

	warehouses = sorted(
		{entry.warehouse for entry in ledger_entries if entry.warehouse}
		| {book.warehouse for book in coupon_books if book.warehouse}
	)
	if filters.get("warehouse") and filters.warehouse not in warehouses:
		warehouses.append(filters.warehouse)
	if not warehouses:
		warehouses = [filters.get("warehouse") or ""]

	report_rows = {
		(coupon_type, warehouse): {
			"coupon_type": coupon_type,
			"warehouse": warehouse,
			"stock_added": 0,
			"generated": 0,
			"issued": 0,
			"returned": 0,
			"closed": 0,
			"remaining": 0,
		}
		for coupon_type in COUPON_TYPES
		for warehouse in warehouses
		if not filters.get("coupon_type") or coupon_type == filters.coupon_type
	}

	for entry in ledger_entries:
		key = (entry.coupon_type, entry.warehouse)
		if key not in report_rows:
			report_rows[key] = {
				"coupon_type": entry.coupon_type,
				"warehouse": entry.warehouse,
				"stock_added": 0,
				"generated": 0,
				"issued": 0,
				"returned": 0,
				"closed": 0,
				"remaining": 0,
			}

		row = report_rows[key]
		if entry.movement_type == "Receipt":
			row["stock_added"] += cint(entry.quantity)

	for book in coupon_books:
		key = (book.coupon_type, book.warehouse)
		if key not in report_rows:
			report_rows[key] = {
				"coupon_type": book.coupon_type,
				"warehouse": book.warehouse,
				"stock_added": 0,
				"generated": 0,
				"issued": 0,
				"returned": 0,
				"closed": 0,
				"remaining": 0,
			}

		report_rows[key]["generated"] += 1
		if book.status == "Issued":
			report_rows[key]["issued"] += 1
		elif book.status == "Returned":
			report_rows[key]["returned"] += 1
		elif book.status == "Closed":
			report_rows[key]["closed"] += 1

	for row in report_rows.values():
		row["remaining"] = row["stock_added"] - row["generated"]

	return sorted(report_rows.values(), key=lambda row: (row["coupon_type"], row["warehouse"] or ""))
