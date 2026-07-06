# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate

from donation_management.donation_management.api import enrich_donor_program_enrollment


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{
			"label": _("Donor"),
			"fieldname": "donor",
			"fieldtype": "Link",
			"options": "Donor",
			"width": 120,
		},
		{
			"label": _("Donor Name"),
			"fieldname": "donor_name",
			"fieldtype": "Data",
			"width": 150,
		},
		{
			"label": _("Program"),
			"fieldname": "sponsorship_program",
			"fieldtype": "Link",
			"options": "Sponsorship Program",
			"width": 160,
		},
		{
			"label": _("Purpose"),
			"fieldname": "donation_purpose",
			"fieldtype": "Link",
			"options": "Donation Purpose",
			"width": 160,
		},
		{
			"label": _("Qty"),
			"fieldname": "quantity",
			"fieldtype": "Int",
			"width": 70,
		},
		{
			"label": _("Total Program Amount"),
			"fieldname": "total_program_amount",
			"fieldtype": "Currency",
			"width": 150,
		},
		{
			"label": _("Paid Amount"),
			"fieldname": "paid_amount",
			"fieldtype": "Currency",
			"width": 130,
		},
		{
			"label": _("Remaining Balance"),
			"fieldname": "remaining_balance",
			"fieldtype": "Currency",
			"width": 140,
		},
		{
			"label": _("Donation Count"),
			"fieldname": "donation_count",
			"fieldtype": "Int",
			"width": 110,
		},
		{
			"label": _("Last Donation Date"),
			"fieldname": "last_donation_date",
			"fieldtype": "Datetime",
			"width": 160,
		},
	]


def get_data(filters):
	conditions = []
	values = {}

	if filters.get("donor"):
		conditions.append("dpe.donor = %(donor)s")
		values["donor"] = filters.donor

	where_clause = f"where {' and '.join(conditions)}" if conditions else ""

	enrollments = frappe.db.sql(
		f"""
		select
			dpe.donor,
			dpe.sponsorship_program,
			dpe.donation_purpose,
			dpe.student_quantity,
			d.customer_name as donor_name
		from `tabDonor Program Enrollment` dpe
		left join `tabDonor` d on d.name = dpe.donor
		{where_clause}
		order by d.customer_name asc, dpe.donor asc, dpe.sponsorship_program asc
		""",
		values,
		as_dict=True,
	)

	rows = []
	for enrollment in enrollments:
		enrich_donor_program_enrollment(enrollment, enrollment.donor)

		rows.append(
			{
				"donor": enrollment.donor,
				"donor_name": enrollment.donor_name,
				"sponsorship_program": enrollment.sponsorship_program,
				"donation_purpose": enrollment.donation_purpose,
				"quantity": cint(enrollment.student_quantity),
				"total_program_amount": flt(enrollment.total_program_amount),
				"paid_amount": flt(enrollment.total_paid),
				"remaining_balance": flt(enrollment.balance),
				"donation_count": get_program_donation_count(
					enrollment.donor,
					enrollment.sponsorship_program,
					filters,
				),
				"last_donation_date": get_program_last_donation_date(
					enrollment.donor,
					enrollment.sponsorship_program,
					filters,
				),
			}
		)

	if not rows and filters.get("donor"):
		rows.extend(get_non_sponsorship_summary(filters))

	return rows


def get_program_donation_count(donor, sponsorship_program, filters):
	conditions = [
		"do.donor_name = %(donor)s",
		"do.docstatus = 1",
		"dosa.sponsorship_program = %(program)s",
	]
	values = {"donor": donor, "program": sponsorship_program}

	if filters.get("company"):
		conditions.append("do.company = %(company)s")
		values["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("date(do.donation_posting_date) >= %(from_date)s")
		values["from_date"] = getdate(filters.from_date)

	if filters.get("to_date"):
		conditions.append("date(do.donation_posting_date) <= %(to_date)s")
		values["to_date"] = getdate(filters.to_date)

	return cint(
		frappe.db.sql(
			f"""
			select count(distinct do.name)
			from `tabDonation Order Sponsorship Allocation` dosa
			inner join `tabDonation Order` do on do.name = dosa.parent
			where {" and ".join(conditions)}
			""",
			values,
		)[0][0]
	)


def get_program_last_donation_date(donor, sponsorship_program, filters):
	conditions = [
		"do.donor_name = %(donor)s",
		"do.docstatus = 1",
		"dosa.sponsorship_program = %(program)s",
	]
	values = {"donor": donor, "program": sponsorship_program}

	if filters.get("company"):
		conditions.append("do.company = %(company)s")
		values["company"] = filters.company

	if filters.get("from_date"):
		conditions.append("date(do.donation_posting_date) >= %(from_date)s")
		values["from_date"] = getdate(filters.from_date)

	if filters.get("to_date"):
		conditions.append("date(do.donation_posting_date) <= %(to_date)s")
		values["to_date"] = getdate(filters.to_date)

	return frappe.db.sql(
		f"""
		select max(do.donation_posting_date)
		from `tabDonation Order Sponsorship Allocation` dosa
		inner join `tabDonation Order` do on do.name = dosa.parent
		where {" and ".join(conditions)}
		""",
		values,
	)[0][0]


def get_non_sponsorship_summary(filters):
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

	summary = frappe.db.sql(
		f"""
		select
			do.donor_name as donor,
			d.customer_name as donor_name,
			count(do.name) as donation_count,
			sum(ifnull(do.donation_amount, 0)) as paid_amount,
			max(do.donation_posting_date) as last_donation_date
		from `tabDonation Order` do
		left join `tabDonor` d on d.name = do.donor_name
		where {" and ".join(conditions)}
			and ifnull(do.purpose_of_donation, '') != 'Sponsorship'
		group by do.donor_name, d.customer_name
		""",
		values,
		as_dict=True,
	)

	return [
		{
			**row,
			"sponsorship_program": _("General Donations"),
			"donation_purpose": "",
			"quantity": 0,
			"total_program_amount": 0,
			"remaining_balance": 0,
			"paid_amount": flt(row.paid_amount),
		}
		for row in summary
		if flt(row.paid_amount) > 0
	]
