import frappe
from frappe.utils import flt


PRISONER_PROGRAM_SUFFIX = " - Prisoner"
PRISONER_MONTHLY_DONATION = 1000


def execute():
	create_prisoner_programs()
	move_legacy_prisoner_allocations()


def create_prisoner_programs():
	programs = frappe.get_all(
		"Sponsorship Program",
		filters={"program_name": ["not like", f"%{PRISONER_PROGRAM_SUFFIX}"]},
		fields=["program_name", "duration_months"],
	)

	for program in programs:
		prisoner_program_name = f"{program.program_name}{PRISONER_PROGRAM_SUFFIX}"
		if frappe.db.exists("Sponsorship Program", prisoner_program_name):
			doc = frappe.get_doc("Sponsorship Program", prisoner_program_name)
		else:
			doc = frappe.new_doc("Sponsorship Program")
			doc.program_name = prisoner_program_name

		doc.duration_months = program.duration_months
		doc.monthly_donation = PRISONER_MONTHLY_DONATION
		doc.total_program_donation = flt(program.duration_months) * PRISONER_MONTHLY_DONATION
		doc.flags.ignore_permissions = True
		doc.save()


def move_legacy_prisoner_allocations():
	if not frappe.db.table_exists("Donation Order Sponsorship Allocation"):
		return

	frappe.db.sql(
		"""
		update `tabDonation Order Sponsorship Allocation`
		set parentfield = 'sponsorship_students'
		where parentfield = 'sponsorship_prisoners'
		"""
	)
