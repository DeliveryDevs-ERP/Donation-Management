import frappe


def execute():
	if not frappe.db.table_exists("Donation Order Sponsorship Allocation"):
		return

	copy_student_rows()
	copy_prisoner_rows()


def copy_student_rows():
	if not frappe.db.table_exists("Donation Order Sponsorship Student"):
		return

	frappe.db.sql(
		"""
		insert into `tabDonation Order Sponsorship Allocation`
			(
				name, creation, modified, modified_by, owner, docstatus,
				parent, parentfield, parenttype, idx,
				student, quantity, sponsorship_program,
				monthly_donation, duration_months, total_program_donation,
				allocated_amount, covered_months, remaining_months, remaining_amount
			)
		select
				old.name, old.creation, old.modified, old.modified_by, old.owner, old.docstatus,
				old.parent, 'sponsorship_students', old.parenttype, old.idx,
				old.student, 1, old.sponsorship_program,
				old.monthly_donation, old.duration_months, old.total_program_donation,
				old.allocated_amount, old.covered_months, old.remaining_months, old.remaining_amount
		from `tabDonation Order Sponsorship Student` old
		where not exists (
			select 1
			from `tabDonation Order Sponsorship Allocation` new
			where new.name = old.name
		)
		"""
	)


def copy_prisoner_rows():
	if not frappe.db.table_exists("Donation Order Sponsorship Prisoner"):
		return

	frappe.db.sql(
		"""
		insert into `tabDonation Order Sponsorship Allocation`
			(
				name, creation, modified, modified_by, owner, docstatus,
				parent, parentfield, parenttype, idx,
				student, quantity, sponsorship_program,
				monthly_donation, duration_months, total_program_donation,
				allocated_amount, covered_months, remaining_months, remaining_amount
			)
		select
				old.name, old.creation, old.modified, old.modified_by, old.owner, old.docstatus,
				old.parent, 'sponsorship_prisoners', old.parenttype, old.idx,
				null, old.quantity, old.sponsorship_program,
				old.monthly_donation, old.duration_months, old.total_program_donation,
				old.allocated_amount, old.covered_months, old.remaining_months, old.remaining_amount
		from `tabDonation Order Sponsorship Prisoner` old
		where not exists (
			select 1
			from `tabDonation Order Sponsorship Allocation` new
			where new.name = old.name
		)
		"""
	)
