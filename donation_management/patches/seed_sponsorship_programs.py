import frappe


PROGRAMS = (
	("Nazra", 24, 2500),
	("Nazra & Hifz", 60, 2500),
	("Hifz ul Quran", 36, 2500),
	("Hifz ul Quran ( Compact )", 5, 1500),
	("Girdan Online ( One to One )", 6, 2500),
	("Girdan Online ( Group )", 7, 1500),
)


def execute():
	for program_name, duration_months, monthly_donation in PROGRAMS:
		if frappe.db.exists("Sponsorship Program", program_name):
			doc = frappe.get_doc("Sponsorship Program", program_name)
		else:
			doc = frappe.new_doc("Sponsorship Program")
			doc.program_name = program_name

		doc.duration_months = duration_months
		doc.monthly_donation = monthly_donation
		doc.total_program_donation = duration_months * monthly_donation
		doc.flags.ignore_permissions = True
		doc.save()
