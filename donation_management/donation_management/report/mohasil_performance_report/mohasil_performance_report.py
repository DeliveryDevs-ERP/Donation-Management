# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate


SOURCES = ("All", "Donation Order", "Box Collection")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	validate_filters(filters)
	rows = get_rows(filters)
	return get_columns(), rows


def validate_filters(filters):
	for fieldname, label in (
		("company", _("Company")),
		("from_date", _("From Date")),
		("to_date", _("To Date")),
	):
		if not filters.get(fieldname):
			frappe.throw(_("{0} is required.").format(label))

	if getdate(filters.from_date) > getdate(filters.to_date):
		frappe.throw(_("From Date cannot be after To Date."))

	filters.source = filters.get("source") or "All"
	if filters.source not in SOURCES:
		frappe.throw(_("Source must be All, Donation Order, or Box Collection."))


def get_columns():
	return [
		{"label": _("Mohasil"), "fieldname": "mohasil", "fieldtype": "Link", "options": "Employee", "width": 140},
		{"label": _("Mohasil Name"), "fieldname": "mohasil_name", "fieldtype": "Data", "width": 180},
		{"label": _("Manual Receipts"), "fieldname": "manual_receipt_count", "fieldtype": "Int", "width": 120},
		{"label": _("Box Collections"), "fieldname": "box_collection_count", "fieldtype": "Int", "width": 120},
		{"label": _("Donation Order Amount"), "fieldname": "donation_order_amount", "fieldtype": "Currency", "width": 160},
		{"label": _("Box Collection Amount"), "fieldname": "box_collection_amount", "fieldtype": "Currency", "width": 160},
		{"label": _("Total Collected Amount"), "fieldname": "total_collected_amount", "fieldtype": "Currency", "width": 170},
		{"label": _("Commission %"), "fieldname": "commission_percentage", "fieldtype": "Float", "width": 110},
		{"label": _("Commission Amount"), "fieldname": "commission_amount", "fieldtype": "Currency", "width": 150},
	]


def get_rows(filters):
	summary = defaultdict(get_blank_summary)

	if filters.source in ("All", "Donation Order"):
		add_donation_order_rows(summary, filters)

	if filters.source in ("All", "Box Collection"):
		add_box_collection_rows(summary, filters)

	commission_percentage = flt(filters.get("commission_percentage"))
	rows = []
	for mohasil in sorted(summary):
		row = summary[mohasil]
		row["total_collected_amount"] = flt(row["donation_order_amount"]) + flt(row["box_collection_amount"])
		row["commission_percentage"] = commission_percentage
		row["commission_amount"] = row["total_collected_amount"] * commission_percentage / 100
		rows.append(row)

	return rows


def get_blank_summary():
	return {
		"mohasil": None,
		"mohasil_name": None,
		"manual_receipt_count": 0,
		"box_collection_count": 0,
		"donation_order_amount": 0,
		"box_collection_amount": 0,
		"total_collected_amount": 0,
		"commission_percentage": 0,
		"commission_amount": 0,
	}


def add_donation_order_rows(summary, filters):
	conditions = [
		"donation_order.docstatus = 1",
		"donation_order.company = %(company)s",
		"donation_order.mohasil is not null",
		"donation_order.mohasil != ''",
		"date(donation_order.donation_posting_date) between %(from_date)s and %(to_date)s",
	]
	values = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}

	if filters.get("mohasil"):
		conditions.append("donation_order.mohasil = %(mohasil)s")
		values["mohasil"] = filters.mohasil

	donation_type_join = ""
	amount_expression = "sum(donation_order.donation_amount)"
	if filters.get("donation_type"):
		donation_type_join = """
			inner join `tabDonation Order Purpose Detail` purpose_detail
				on purpose_detail.parent = donation_order.name
				and purpose_detail.parenttype = 'Donation Order'
				and purpose_detail.parentfield = 'purpose_details'
				and purpose_detail.donation_type = %(donation_type)s
		"""
		amount_expression = "sum(purpose_detail.amount)"
		values["donation_type"] = filters.donation_type

	rows = frappe.db.sql(
		f"""
		select
			donation_order.mohasil,
			employee.employee_name as mohasil_name,
			count(distinct donation_order.name) as receipt_count,
			{amount_expression} as amount
		from `tabDonation Order` donation_order
		{donation_type_join}
		inner join `tabEmployee` employee
			on employee.name = donation_order.mohasil
			and employee.designation = 'Mohasil'
		where {" and ".join(conditions)}
		group by donation_order.mohasil, employee.employee_name
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		target = summary[row.mohasil]
		target["mohasil"] = row.mohasil
		target["mohasil_name"] = row.mohasil_name
		target["manual_receipt_count"] += row.receipt_count
		target["donation_order_amount"] += flt(row.amount)


def add_box_collection_rows(summary, filters):
	conditions = [
		"box_collection.docstatus = 1",
		"box_collection.company = %(company)s",
		"collection_log.action = 'Collection'",
		"collection_log.staff is not null",
		"collection_log.staff != ''",
		"date(collection_log.action_date) between %(from_date)s and %(to_date)s",
	]
	values = {
		"company": filters.company,
		"from_date": filters.from_date,
		"to_date": filters.to_date,
	}

	if filters.get("mohasil"):
		conditions.append("collection_log.staff = %(mohasil)s")
		values["mohasil"] = filters.mohasil

	if filters.get("donation_type"):
		conditions.append("collection_log.donation_head = %(donation_type)s")
		values["donation_type"] = filters.donation_type

	rows = frappe.db.sql(
		f"""
		select
			collection_log.staff as mohasil,
			employee.employee_name as mohasil_name,
			count(collection_log.name) as collection_count,
			sum(collection_log.collected_amount) as amount
		from `tabBox Collection Log` collection_log
		inner join `tabBox Collection` box_collection
			on box_collection.name = collection_log.box_collection
		inner join `tabEmployee` employee
			on employee.name = collection_log.staff
			and employee.designation = 'Mohasil'
		where {" and ".join(conditions)}
		group by collection_log.staff, employee.employee_name
		""",
		values,
		as_dict=True,
	)

	for row in rows:
		target = summary[row.mohasil]
		target["mohasil"] = row.mohasil
		target["mohasil_name"] = row.mohasil_name
		target["box_collection_count"] += row.collection_count
		target["box_collection_amount"] += flt(row.amount)
