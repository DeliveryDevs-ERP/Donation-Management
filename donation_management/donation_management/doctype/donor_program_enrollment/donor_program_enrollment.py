# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class DonorProgramEnrollment(Document):
	def before_insert(self):
		if not self.flags.from_donation_order:
			frappe.throw(
				frappe._(
					"Donor Program Enrollment is created automatically from submitted Donation Orders."
				)
			)

	def validate(self):
		self.student_quantity = max(cint(self.student_quantity), 1)


def upsert_donor_program_enrollment(donor, sponsorship_program, student_quantity, donation_purpose=None, donation_order=None):
	if not donor or not sponsorship_program:
		return

	student_quantity = max(cint(student_quantity), 1)
	existing = frappe.db.exists(
		"Donor Program Enrollment",
		{"donor": donor, "sponsorship_program": sponsorship_program},
	)

	if existing:
		doc = frappe.get_doc("Donor Program Enrollment", existing)
		doc.student_quantity = student_quantity
		if donation_purpose:
			doc.donation_purpose = donation_purpose
		if donation_order:
			doc.last_donation_order = donation_order
		doc.save(ignore_permissions=True)
		return doc.name

	doc = frappe.get_doc(
		{
			"doctype": "Donor Program Enrollment",
			"donor": donor,
			"sponsorship_program": sponsorship_program,
			"donation_purpose": donation_purpose,
			"student_quantity": student_quantity,
			"last_donation_order": donation_order,
		}
	)
	doc.flags.from_donation_order = True
	doc.insert(ignore_permissions=True)
	return doc.name
