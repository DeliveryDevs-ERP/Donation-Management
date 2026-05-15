# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, getdate, now_datetime

from donation_management.donation_management.doctype.donor.donor import normalize_cnic, normalize_phone
from donation_management.donation_management.api import (
	account_matches_donation_type,
	get_default_company,
	get_donation_purpose_account_mapping,
	get_mode_of_payment_account,
)


SPONSORSHIP_PURPOSE = "Sponsorship"


def ensure_donor_party_type():
	if not frappe.db.exists("Party Type", "Donor"):
		frappe.get_doc(
			{"doctype": "Party Type", "party_type": "Donor", "account_type": "Receivable"}
		).insert(ignore_permissions=True)


def get_donor_receivable_account(company):
	return (
		frappe.db.get_value(
			"Account",
			{
				"company": company,
				"account_type": "Receivable",
				"account_name": ["like", "%Donation%"],
				"is_group": 0,
			},
			"name",
		)
		or frappe.db.get_value(
			"Account",
			{"company": company, "account_type": "Receivable", "is_group": 0},
			"name",
		)
	)


class DonationOrder(Document):
	def validate(self):
		if not self.donation_posting_date:
			self.donation_posting_date = now_datetime()

		self.set_company_defaults()
		self.set_donor_details()
		self.set_purpose_details()
		self.validate_purpose()
		self.set_previous_sponsorship_balance()
		self.set_sponsorship_allocations()
		self.validate_beneficiary()
		self.set_total_donation()
		self.set_accounting_details()
		self.validate_accounting_details()
		self.validate_posted_accounting_locked()

	def on_update(self):
		self.sync_sponsorship_balance_ledger()
		self.create_journal_entry()
		self.create_payment_entry()

	def on_trash(self):
		self.cancel_linked_journal_entry()
		self.cancel_linked_payment_entry()

	def is_sponsorship(self):
		return self.purpose_of_donation == SPONSORSHIP_PURPOSE

	def set_company_defaults(self):
		if not self.company:
			self.company = get_default_company()

		if self.company and not self.currency:
			self.currency = frappe.db.get_value("Company", self.company, "default_currency")

	def set_donor_details(self):
		if self.donor_cnic:
			self.donor_cnic = normalize_cnic(self.donor_cnic)

		if not self.donor_name and self.donor_cnic:
			self.donor_name = frappe.db.get_value("Donor", {"donor_cnic": self.donor_cnic}, "name")

		if not self.donor_name and self.donor_phone_number:
			self.donor_name = frappe.db.get_value(
				"Donor",
				{"donor_phone_digits": normalize_phone(self.donor_phone_number)},
				"name",
			)

		if not self.donor_name:
			frappe.throw(frappe._("Donor is required."))

		donor = frappe.db.get_value(
			"Donor",
			self.donor_name,
			["name", "customer_name", "donor_cnic", "donor_phone_number", "donor_phone_digits", "referred_by_trustee"],
			as_dict=True,
		)
		if not donor:
			frappe.throw(frappe._("Donor {0} was not found.").format(self.donor_name))

		if self.donor_cnic and donor.donor_cnic and self.donor_cnic != donor.donor_cnic:
			frappe.throw(
				frappe._("Donor CNIC {0} does not match selected Donor {1}.").format(
					self.donor_cnic,
					donor.name,
				)
			)

		if self.donor_cnic and not donor.donor_cnic:
			frappe.throw(
				frappe._("Selected Donor {0} does not have CNIC {1}.").format(
					donor.name,
					self.donor_cnic,
				)
			)

		if self.donor_phone_number:
			donor_phone_digits = normalize_phone(self.donor_phone_number)
			if donor.donor_phone_digits and donor_phone_digits != donor.donor_phone_digits:
				frappe.throw(
					frappe._("Donor Phone Number {0} does not match selected Donor {1}.").format(
						self.donor_phone_number,
						donor.name,
					)
				)

			if donor_phone_digits and not donor.donor_phone_digits:
				frappe.throw(
					frappe._("Selected Donor {0} does not have Phone Number {1}.").format(
						donor.name,
						self.donor_phone_number,
					)
				)

		self.donor_cnic = donor.donor_cnic or None
		self.donor_phone_number = donor.donor_phone_number
		self.referred_by_trustee = donor.referred_by_trustee
		if not self.name_on_donation_slip:
			self.name_on_donation_slip = donor.customer_name

	def set_purpose_details(self):
		if not self.donation_purpose:
			self.requires_student = 0
			self.requires_prisoner = 0
			self.student_mode = None
			self.purpose_path = None
			return

		purpose = frappe.get_cached_doc("Donation Purpose", self.donation_purpose)
		self.requires_student = purpose.requires_student
		self.requires_prisoner = purpose.requires_prisoner
		self.student_mode = purpose.student_mode
		self.purpose_path = purpose.purpose_path

	def validate_purpose(self):
		if not self.donation_purpose:
			return

		purpose = frappe.get_cached_doc("Donation Purpose", self.donation_purpose)
		if purpose.is_group:
			frappe.throw(frappe._("Please select a leaf Donation Purpose, not a group."))

		if self.purpose_of_donation and purpose.purpose_group != self.purpose_of_donation:
			frappe.throw(
				frappe._("Donation Purpose {0} belongs to {1}, not {2}.").format(
					self.donation_purpose,
					purpose.purpose_group,
					self.purpose_of_donation,
				)
			)

	def validate_beneficiary(self):
		if self.is_sponsorship():
			self.student_name = None
			self.student_mode = None
			self.prisoner_name = None
			return

		if self.requires_student and not self.student_name:
			frappe.throw(frappe._("Student is required for the selected Donation Purpose."))

		if self.requires_prisoner and not self.prisoner_name:
			frappe.throw(frappe._("Prisoner is required for the selected Donation Purpose."))

		if not self.requires_student:
			self.student_name = None
			self.student_mode = None

		if not self.requires_prisoner:
			self.prisoner_name = None

	def set_sponsorship_allocations(self):
		if not self.is_sponsorship():
			self.sponsorship_students = []
			self.sponsorship_prisoners = []
			self.previous_sponsorship_balance = 0
			self.previous_balance_used = 0
			self.available_allocation_amount = 0
			self.allocated_amount = 0
			self.unallocated_amount = 0
			self.allocation_status = None
			self.total_sponsored_beneficiaries = 0
			self.total_covered_months = 0
			return

		if not self.donation_purpose:
			self.reset_sponsorship_summary()
			return

		if not self.requires_student and not self.requires_prisoner:
			self.sponsorship_students = []
			self.sponsorship_prisoners = []
			self.reset_sponsorship_summary()
			return

		if self.requires_student:
			self.sponsorship_prisoners = []
			if not self.sponsorship_students:
				frappe.throw(frappe._("At least one Sponsorship Student row is required."))
			self.validate_unique_sponsorship_students()

		if self.requires_prisoner:
			self.sponsorship_students = []
			if not self.sponsorship_prisoners:
				frappe.throw(frappe._("At least one Sponsorship Prisoner row is required."))

		allocated_amount = 0
		total_sponsored_beneficiaries = 0
		total_covered_months = 0

		for row in self.sponsorship_students:
			self.set_sponsorship_student_row(row)
			allocated_amount += flt(row.allocated_amount)
			total_sponsored_beneficiaries += 1
			total_covered_months += flt(row.covered_months)

		for row in self.sponsorship_prisoners:
			self.set_sponsorship_prisoner_row(row)
			allocated_amount += flt(row.allocated_amount)
			total_sponsored_beneficiaries += cint(row.quantity)
			total_covered_months += flt(row.covered_months)

		if allocated_amount > flt(self.available_allocation_amount):
			frappe.throw(
				frappe._("Allocated Amount {0} cannot be greater than Available Allocation Amount {1}.").format(
					frappe.format_value(allocated_amount, {"fieldtype": "Currency"}),
					frappe.format_value(self.available_allocation_amount, {"fieldtype": "Currency"}),
				)
			)

		self.allocated_amount = allocated_amount
		self.unallocated_amount = flt(self.available_allocation_amount) - allocated_amount
		self.set_allocation_status()
		self.total_sponsored_beneficiaries = total_sponsored_beneficiaries
		self.total_covered_months = total_covered_months

	def set_previous_sponsorship_balance(self):
		if not self.is_sponsorship():
			self.previous_sponsorship_balance = 0
			self.previous_balance_used = 0
			self.available_allocation_amount = 0
			return

		if not self.donor_name:
			self.previous_sponsorship_balance = 0
			self.previous_balance_used = 0
			self.available_allocation_amount = flt(self.donation_amount)
			return

		self.previous_sponsorship_balance = self.get_donor_previous_sponsorship_balance()
		self.previous_balance_used = self.previous_sponsorship_balance
		self.available_allocation_amount = flt(self.donation_amount) + flt(self.previous_balance_used)

	def get_donor_previous_sponsorship_balance(self):
		filters = {
			"donor_name": self.donor_name,
			"purpose_of_donation": SPONSORSHIP_PURPOSE,
			"name": ["!=", self.name],
			"docstatus": ["!=", 2],
		}
		if not self.is_new() and self.creation:
			filters["creation"] = ["<", self.creation]

		donation_amount = frappe.db.get_value(
			"Donation Order",
			filters,
			"sum(donation_amount)",
		)
		allocated_amount = frappe.db.get_value(
			"Donation Order",
			filters,
			"sum(allocated_amount)",
		)
		return max(flt(donation_amount) - flt(allocated_amount), 0)

	def validate_unique_sponsorship_students(self):
		selected_students = {}
		for row in self.sponsorship_students:
			if not row.student:
				continue

			if row.student in selected_students:
				frappe.throw(
					frappe._("Student {0} is already selected in row {1}.").format(
						row.student,
						selected_students[row.student],
					)
				)

			selected_students[row.student] = row.idx

	def reset_sponsorship_summary(self):
		self.available_allocation_amount = flt(self.donation_amount) + flt(self.previous_balance_used)
		self.allocated_amount = 0
		self.unallocated_amount = self.available_allocation_amount if self.is_sponsorship() else 0
		self.allocation_status = "Unallocated" if self.is_sponsorship() else None
		self.total_sponsored_beneficiaries = 0
		self.total_covered_months = 0

	def set_allocation_status(self):
		if not self.is_sponsorship():
			self.allocation_status = None
			return

		if flt(self.allocated_amount) <= 0:
			self.allocation_status = "Unallocated"
		elif flt(self.unallocated_amount) > 0:
			self.allocation_status = "Partially Allocated"
		else:
			self.allocation_status = "Fully Allocated"

	def set_sponsorship_student_row(self, row):
		if not row.student:
			frappe.throw(frappe._("Student is required in Sponsorship Student rows."))

		row.quantity = 1
		self.set_sponsorship_row_program_details(row, quantity=1, row_label="Sponsorship Student")

	def set_sponsorship_prisoner_row(self, row):
		if cint(row.quantity) <= 0:
			frappe.throw(frappe._("Quantity must be greater than zero in Sponsorship Prisoners."))

		row.student = None
		self.set_sponsorship_row_program_details(
			row,
			quantity=cint(row.quantity),
			row_label="Sponsorship Prisoner",
		)

	def set_sponsorship_row_program_details(self, row, quantity, row_label):
		if not row.sponsorship_program:
			frappe.throw(frappe._("Sponsorship Program is required in {0} rows.").format(row_label))

		program = frappe.get_cached_doc("Sponsorship Program", row.sponsorship_program)
		row.monthly_donation = flt(program.monthly_donation)
		row.duration_months = cint(program.duration_months)
		row.total_program_donation = flt(row.monthly_donation) * cint(row.duration_months) * quantity

		if flt(row.allocated_amount) <= 0:
			frappe.throw(frappe._("Allocated Amount must be greater than zero in {0} rows.").format(row_label))

		if flt(row.allocated_amount) > flt(row.total_program_donation):
			frappe.throw(
				frappe._("Allocated Amount cannot exceed Total Program Donation for row {0}.").format(row.idx)
			)

		monthly_total = flt(row.monthly_donation) * quantity
		row.covered_months = min(flt(row.allocated_amount) / monthly_total, flt(row.duration_months))
		row.remaining_months = max(flt(row.duration_months) - flt(row.covered_months), 0)
		row.remaining_amount = max(flt(row.total_program_donation) - flt(row.allocated_amount), 0)

	def sync_sponsorship_balance_ledger(self):
		if not frappe.db.table_exists("Sponsorship Balance Ledger"):
			return

		frappe.db.delete("Sponsorship Balance Ledger", {"donation_order": self.name})
		if not self.is_sponsorship():
			return

		balance = flt(self.donation_amount) + flt(self.previous_balance_used)
		self.create_sponsorship_ledger_entry(
			entry_type="Donation Received",
			amount_in=flt(self.donation_amount),
			amount_allocated=0,
			balance_after_entry=flt(self.donation_amount),
		)

		if flt(self.previous_balance_used) > 0:
			self.create_sponsorship_ledger_entry(
				entry_type="Previous Balance Used",
				amount_in=flt(self.previous_balance_used),
				amount_allocated=0,
				balance_after_entry=balance,
			)

		for row in self.sponsorship_students:
			if flt(row.allocated_amount) <= 0:
				continue

			balance -= flt(row.allocated_amount)
			self.create_sponsorship_ledger_entry(
				entry_type="Student Allocation",
				amount_in=0,
				amount_allocated=flt(row.allocated_amount),
				balance_after_entry=balance,
				beneficiary_type="Student",
				student=row.student,
				quantity=1,
				sponsorship_program=row.sponsorship_program,
				allocation_row_name=row.name,
			)

		for row in self.sponsorship_prisoners:
			if flt(row.allocated_amount) <= 0:
				continue

			balance -= flt(row.allocated_amount)
			self.create_sponsorship_ledger_entry(
				entry_type="Prisoner Allocation",
				amount_in=0,
				amount_allocated=flt(row.allocated_amount),
				balance_after_entry=balance,
				beneficiary_type="Prisoner",
				quantity=cint(row.quantity),
				sponsorship_program=row.sponsorship_program,
				allocation_row_name=row.name,
			)

	def create_sponsorship_ledger_entry(
		self,
		entry_type,
		amount_in,
		amount_allocated,
		balance_after_entry,
		beneficiary_type=None,
		student=None,
		quantity=None,
		sponsorship_program=None,
		allocation_row_name=None,
	):
		frappe.get_doc(
			{
				"doctype": "Sponsorship Balance Ledger",
				"donor": self.donor_name,
				"donation_order": self.name,
				"posting_datetime": now_datetime(),
				"entry_type": entry_type,
				"amount_in": amount_in,
				"amount_allocated": amount_allocated,
				"balance_after_entry": balance_after_entry,
				"beneficiary_type": beneficiary_type,
				"student": student,
				"quantity": quantity,
				"sponsorship_program": sponsorship_program,
				"allocation_row_name": allocation_row_name,
			}
		).insert(ignore_permissions=True)

	def set_total_donation(self):
		if self.is_sponsorship():
			self.total_donation = flt(self.donation_amount)
			return

		if not self.student_name:
			self.total_donation = 0
			return

		existing_total = frappe.db.get_value(
			"Donation Order",
			{
				"student_name": self.student_name,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
			"sum(donation_amount)",
		)
		self.total_donation = flt(existing_total) + flt(self.donation_amount)

	def set_accounting_details(self):
		self.accounting_status = self.accounting_status or "Not Posted"

		if self.mode_of_payment and self.company:
			mode_details = get_mode_of_payment_account(self.company, self.mode_of_payment, self.donation_type)
			self.mode_of_payment_type = mode_details.get("mode_of_payment_type")
			if self.mode_of_payment_type == "Bank":
				if not self.bank_account:
					self.bank_account = mode_details.get("debit_account")
				self.debit_account = self.bank_account
			else:
				self.bank_account = None
				if not self.debit_account:
					self.debit_account = mode_details.get("debit_account")
		else:
			self.mode_of_payment_type = None
			self.bank_account = None

		if self.donation_purpose and self.donation_type and self.company:
			mapping = get_donation_purpose_account_mapping(
				self.company,
				self.donation_type,
				self.donation_purpose,
			)
			if not self.credit_account:
				self.credit_account = mapping.get("credit_account")
			if not self.accounting_cost_center:
				self.accounting_cost_center = mapping.get("cost_center")
		else:
			if not self.credit_account:
				self.credit_account = None

	def validate_accounting_details(self):
		if flt(self.donation_amount) <= 0:
			frappe.throw(frappe._("Donation Amount must be greater than zero."))

		if not self.company:
			frappe.throw(frappe._("Company is required for accounting."))

		if not self.mode_of_payment:
			frappe.throw(frappe._("Mode of Payment is required for accounting."))

		if not self.debit_account:
			frappe.throw(frappe._("Debit Account is required for accounting."))

		if not self.credit_account:
			frappe.throw(
				frappe._(
					"Credit Account mapping is required for Donation Purpose {0} and Donation Type {1}."
				).format(self.donation_purpose, self.donation_type)
			)

		self.validate_account(self.debit_account, "Debit Account")
		self.validate_account(
			self.credit_account,
			"Credit Account",
			allowed_root_types=("Income", "Liability", "Equity"),
		)

		if self.mode_of_payment_type in ("Cash", "Bank"):
			account_type = frappe.db.get_value("Account", self.debit_account, "account_type")
			if account_type != self.mode_of_payment_type:
				frappe.throw(
					frappe._("Debit Account must be a {0} account for Mode of Payment {1}.").format(
						self.mode_of_payment_type,
						self.mode_of_payment,
					)
				)

		if self.mode_of_payment_type == "Bank" and self.donation_type:
			if not account_matches_donation_type(self.debit_account, self.donation_type):
				frappe.throw(
					frappe._("Debit Account must contain {0} for Bank donations of type {0}.").format(
						self.donation_type
					)
				)

	def validate_account(self, account, label, allowed_account_types=None, allowed_root_types=None):
		account_details = frappe.db.get_value(
			"Account",
			account,
			["name", "company", "is_group", "account_type", "root_type"],
			as_dict=True,
		)
		if not account_details:
			frappe.throw(frappe._("{0} {1} was not found.").format(label, account))

		if account_details.company != self.company:
			frappe.throw(
				frappe._("{0} {1} does not belong to Company {2}.").format(label, account, self.company)
			)

		if account_details.is_group:
			frappe.throw(frappe._("{0} {1} cannot be a group account.").format(label, account))

		if allowed_account_types and account_details.account_type not in allowed_account_types:
			frappe.throw(
				frappe._("{0} {1} must be one of these account types: {2}.").format(
					label,
					account,
					", ".join(allowed_account_types),
				)
			)

		if allowed_root_types and account_details.root_type not in allowed_root_types:
			frappe.throw(
				frappe._("{0} {1} must be one of these root types: {2}.").format(
					label,
					account,
					", ".join(allowed_root_types),
				)
			)

	def validate_posted_accounting_locked(self):
		old_doc = self.get_doc_before_save()
		if not old_doc or not old_doc.journal_entry:
			return

		journal_entry_status = frappe.db.get_value("Journal Entry", old_doc.journal_entry, "docstatus")
		if journal_entry_status != 1:
			return

		locked_fields = (
			"donor_name",
			"company",
			"donation_posting_date",
			"mode_of_payment",
			"bank_account",
			"debit_account",
			"donation_type",
			"donation_purpose",
			"credit_account",
			"donation_amount",
		)
		for fieldname in locked_fields:
			if str(old_doc.get(fieldname) or "") != str(self.get(fieldname) or ""):
				frappe.throw(
					frappe._("Cannot change {0} after Journal Entry {1} has been posted.").format(
						self.meta.get_label(fieldname),
						old_doc.journal_entry,
					)
				)

	def create_journal_entry(self):
		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			self.set_accounting_status_from_journal_entry()
			return

		existing_journal_entry = frappe.db.get_value(
			"Journal Entry",
			{
				"user_remark": ["in", [self.get_journal_entry_user_remark(), self.get_legacy_journal_entry_user_remark()]],
				"docstatus": ["!=", 2],
			},
			"name",
		)
		if existing_journal_entry:
			self.set_gl_entry_party(existing_journal_entry)
			self.set_accounting_fields(existing_journal_entry, "Posted")
			return

		cost_center = self.accounting_cost_center or frappe.db.get_value(
			"Company",
			self.company,
			"cost_center",
		)
		entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": getdate(self.donation_posting_date),
				"pay_to_recd_from": self.get_journal_entry_received_from(),
				"user_remark": self.get_journal_entry_user_remark(),
				"accounts": [
					self.get_journal_entry_account_row(
						account=self.debit_account,
						debit=flt(self.donation_amount),
						credit=0,
						cost_center=cost_center,
					),
					self.get_journal_entry_account_row(
						account=self.credit_account,
						debit=0,
						credit=flt(self.donation_amount),
						cost_center=cost_center,
					),
				],
			}
		)
		entry.insert(ignore_permissions=True)
		entry.submit()
		self.set_gl_entry_party(entry.name)
		self.set_accounting_fields(entry.name, "Posted")

	def get_journal_entry_account_row(self, account, debit, credit, cost_center=None):
		account_type = frappe.db.get_value("Account", account, "account_type")
		row = {
			"account": account,
			"debit_in_account_currency": debit,
			"credit_in_account_currency": credit,
			"user_remark": "Donor: {0}".format(self.donor_name),
		}
		if account_type in ("Receivable", "Payable", "Equity"):
			row.update(
				{
					"party_type": "Donor",
					"party": self.donor_name,
				}
			)

		if cost_center:
			row["cost_center"] = cost_center

		return row

	def get_journal_entry_user_remark(self):
		return "Donation Order: {0} | Donor: {1}".format(self.name, self.donor_name)

	def get_legacy_journal_entry_user_remark(self):
		return "Donation Order: {0}".format(self.name)

	def get_journal_entry_received_from(self):
		donor_name = frappe.db.get_value("Donor", self.donor_name, "customer_name")
		return "{0} ({1})".format(donor_name or self.donor_name, self.donor_name)

	def set_accounting_fields(self, journal_entry, status):
		frappe.db.set_value(
			self.doctype,
			self.name,
			{
				"journal_entry": journal_entry,
				"accounting_status": status,
			},
			update_modified=False,
		)
		self.journal_entry = journal_entry
		self.accounting_status = status

	def set_accounting_status_from_journal_entry(self):
		docstatus = frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus")
		status = "Posted" if docstatus == 1 else "Cancelled" if docstatus == 2 else "Not Posted"
		self.set_accounting_fields(self.journal_entry, status)

	def cancel_linked_journal_entry(self):
		if not self.journal_entry or not frappe.db.exists("Journal Entry", self.journal_entry):
			return

		entry = frappe.get_doc("Journal Entry", self.journal_entry)
		if entry.docstatus == 1:
			entry.cancel()
			self.accounting_status = "Cancelled"

	def create_payment_entry(self):
		if self.payment_entry and frappe.db.exists("Payment Entry", self.payment_entry):
			return

		existing = frappe.db.get_value(
			"Payment Entry",
			{"reference_no": self.name, "docstatus": ["!=", 2]},
			"name",
		)
		if existing:
			frappe.db.set_value(self.doctype, self.name, "payment_entry", existing, update_modified=False)
			self.payment_entry = existing
			return

		try:
			ensure_donor_party_type()
			paid_from = get_donor_receivable_account(self.company)
			if not paid_from:
				frappe.log_error(
					"No receivable account found for company {0}; skipping Payment Entry for Donation Order {1}.".format(
						self.company, self.name
					),
					"Donation Order Payment Entry",
				)
				return

			donor_display_name = frappe.db.get_value("Donor", self.donor_name, "customer_name") or self.donor_name
			pe = frappe.get_doc(
				{
					"doctype": "Payment Entry",
					"payment_type": "Receive",
					"party_type": "Donor",
					"party": self.donor_name,
					"party_name": donor_display_name,
					"company": self.company,
					"posting_date": getdate(self.donation_posting_date),
					"mode_of_payment": self.mode_of_payment,
					"paid_from": paid_from,
					"paid_from_account_currency": self.currency,
					"paid_to": self.debit_account,
					"paid_to_account_currency": self.currency,
					"paid_amount": flt(self.donation_amount),
					"received_amount": flt(self.donation_amount),
					"reference_no": self.name,
					"reference_date": getdate(self.donation_posting_date),
					"remarks": "Donation Order: {0} | Donor: {1}".format(self.name, self.donor_name),
				}
			)
			pe.insert(ignore_permissions=True)
			frappe.db.set_value(self.doctype, self.name, "payment_entry", pe.name, update_modified=False)
			self.payment_entry = pe.name
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Donation Order Payment Entry Creation Failed")

	def cancel_linked_payment_entry(self):
		if not self.payment_entry or not frappe.db.exists("Payment Entry", self.payment_entry):
			return

		entry = frappe.get_doc("Payment Entry", self.payment_entry)
		if entry.docstatus == 1:
			entry.cancel()
		elif entry.docstatus == 0:
			entry.delete()

	def set_gl_entry_party(self, journal_entry):
		# ERPNext blocks party fields on Bank/Income Journal Entry rows, but JTQ needs
		# donor-wise General Ledger reporting. Set party on generated GL rows only.
		frappe.db.sql(
			"""
			update `tabGL Entry`
			set party_type = %s,
				party = %s
			where voucher_type = 'Journal Entry'
				and voucher_no = %s
				and ifnull(is_cancelled, 0) = 0
			""",
			("Donor", self.donor_name, journal_entry),
		)
