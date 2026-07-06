# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	if not filters.get("donor"):
		frappe.throw(_("Donor is required."))

	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Posting Date"),
			"fieldname": "posting_date",
			"fieldtype": "Datetime",
			"width": 150,
		},
		{
			"label": _("Donation Order"),
			"fieldname": "donation_order",
			"fieldtype": "Link",
			"options": "Donation Order",
			"width": 130,
		},
		{
			"label": _("Donation Type"),
			"fieldname": "donation_type",
			"fieldtype": "Data",
			"width": 90,
		},
		{
			"label": _("Category"),
			"fieldname": "donation_category",
			"fieldtype": "Data",
			"width": 110,
		},
		{
			"label": _("Purpose"),
			"fieldname": "donation_purpose",
			"fieldtype": "Link",
			"options": "Donation Purpose",
			"width": 160,
		},
		{
			"label": _("Program"),
			"fieldname": "sponsorship_program",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"width": 120,
		},
		{
			"label": _("Allocated Amount"),
			"fieldname": "allocated_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Total Program Amount"),
			"fieldname": "total_program_amount",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Remaining After Payment"),
			"fieldname": "remaining_program_balance",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Mode of Payment"),
			"fieldname": "mode_of_payment",
			"fieldtype": "Link",
			"options": "Mode of Payment",
			"width": 120,
		},
		{
			"label": _("Journal Entry"),
			"fieldname": "journal_entry",
			"fieldtype": "Link",
			"options": "Journal Entry",
			"width": 130,
		},
		{
			"label": _("Running Total Paid"),
			"fieldname": "running_balance",
			"fieldtype": "Currency",
			"width": 130,
		},
	]


def get_data(filters):
	conditions = ["do.docstatus = 1", "do.donor_name = %(donor)s"]
	values = {"donor": filters.donor}

	if filters.get("company"):
		conditions.append("do.company = %(company)s")
		values["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("date(do.donation_posting_date) >= %(from_date)s")
		values["from_date"] = getdate(filters.from_date)

	if filters.get("to_date"):
		conditions.append("date(do.donation_posting_date) <= %(to_date)s")
		values["to_date"] = getdate(filters.to_date)

	orders = frappe.db.sql(
		f"""
		select
			do.donation_posting_date as posting_date,
			do.name as donation_order,
			do.donation_type,
			do.purpose_of_donation as donation_category,
			do.donation_purpose,
			do.donation_amount as paid_amount,
			do.allocated_amount,
			do.total_program_amount,
			do.mode_of_payment,
			do.journal_entry
		from `tabDonation Order` do
		where {" and ".join(conditions)}
		order by do.donation_posting_date asc, do.name asc
		""",
		values,
		as_dict=True,
	)

	program_paid_totals = {}
	running_balance = 0
	data_rows = []

	for order in orders:
		running_balance += flt(order.paid_amount)
		programs = get_order_programs(order.donation_order)
		program_label = ", ".join(programs) if programs else ""

		remaining_after = 0
		if order.donation_category == "Sponsorship" and programs:
			for program in programs:
				program_total = get_program_total_amount(filters.donor, program)
				allocated = get_order_program_allocated(order.donation_order, program)
				program_paid_totals[program] = program_paid_totals.get(program, 0) + allocated
				remaining_after = max(program_total - program_paid_totals[program], remaining_after)

		data_rows.append(
			{
				"posting_date": order.posting_date,
				"donation_order": order.donation_order,
				"donation_type": order.donation_type,
				"donation_category": order.donation_category,
				"donation_purpose": order.donation_purpose,
				"sponsorship_program": program_label,
				"paid_amount": flt(order.paid_amount),
				"allocated_amount": flt(order.allocated_amount),
				"total_program_amount": flt(order.total_program_amount) or get_program_total_amount(
					filters.donor, programs[0]
				)
				if programs
				else 0,
				"remaining_program_balance": remaining_after,
				"mode_of_payment": order.mode_of_payment,
				"journal_entry": order.journal_entry,
				"running_balance": running_balance,
			}
		)

	if data_rows:
		data_rows.append(
			{
				"sponsorship_program": _("Total"),
				"paid_amount": sum(flt(row.get("paid_amount")) for row in data_rows),
				"allocated_amount": sum(flt(row.get("allocated_amount")) for row in data_rows),
				"remaining_program_balance": data_rows[-1].get("remaining_program_balance"),
				"running_balance": running_balance,
				"is_total_row": 1,
			}
		)

	return data_rows


def get_order_programs(donation_order):
	return frappe.get_all(
		"Donation Order Sponsorship Allocation",
		filters={"parent": donation_order},
		pluck="sponsorship_program",
	)


def get_order_program_allocated(donation_order, sponsorship_program):
	return flt(
		frappe.db.get_value(
			"Donation Order Sponsorship Allocation",
			{"parent": donation_order, "sponsorship_program": sponsorship_program},
			"allocated_amount",
		)
	)


def get_program_total_amount(donor, sponsorship_program):
	quantity = frappe.db.get_value(
		"Donor Program Enrollment",
		{"donor": donor, "sponsorship_program": sponsorship_program},
		"student_quantity",
	)
	if not quantity:
		return 0

	program = frappe.db.get_value(
		"Sponsorship Program",
		sponsorship_program,
		["monthly_donation", "duration_months"],
		as_dict=True,
	)
	if not program:
		return 0

	return flt(program.monthly_donation) * cint(program.duration_months) * cint(quantity)
