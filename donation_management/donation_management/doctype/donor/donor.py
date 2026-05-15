# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.model.document import Document


VALID_DONOR_TYPES = ("Walk-in", "Refered by Trustee")


class Donor(Document):
	def validate(self):
		self.set_donor_type()
		self.set_trustee_reference()
		self.set_donor_cnic()
		self.set_donor_phone_digits()
		self.validate_unique_donor_cnic()
		self.validate_unique_donor_phone()

	def set_donor_type(self):
		if self.customer_type not in VALID_DONOR_TYPES:
			self.customer_type = "Walk-in"

	def set_trustee_reference(self):
		if self.customer_type == "Walk-in":
			self.referred_by_trustee = None
			return

		if not self.referred_by_trustee:
			frappe.throw(frappe._("Referred By Trustee is required."))

		if self.referred_by_trustee == self.name:
			frappe.throw(frappe._("Referred By Trustee cannot refer to the same Donor."))

		trustee = frappe.db.exists("Trustee", self.referred_by_trustee)
		if not trustee:
			frappe.throw(frappe._("Referred By Trustee {0} was not found.").format(self.referred_by_trustee))

	def set_donor_cnic(self):
		if not self.donor_cnic:
			return

		self.donor_cnic = normalize_cnic(self.donor_cnic)

	def set_donor_phone_digits(self):
		self.donor_phone_digits = normalize_phone(self.donor_phone_number) or None

	def validate_unique_donor_cnic(self):
		if not self.donor_cnic:
			return

		existing_donor = frappe.db.exists(
			"Donor",
			{
				"donor_cnic": self.donor_cnic,
				"name": ["!=", self.name],
			},
		)
		if existing_donor:
			frappe.throw(
				frappe._("Donor CNIC {0} is already used by Donor {1}.").format(
					self.donor_cnic,
					existing_donor,
				)
			)

	def validate_unique_donor_phone(self):
		if not self.donor_phone_digits:
			return

		existing_donor = frappe.db.exists(
			"Donor",
			{
				"donor_phone_digits": self.donor_phone_digits,
				"name": ["!=", self.name],
			},
		)
		if existing_donor:
			frappe.throw(
				frappe._("Donor Phone Number {0} is already used by Donor {1}.").format(
					self.donor_phone_number,
					existing_donor,
				)
			)


def normalize_cnic(cnic):
	cnic = re.sub(r"\D", "", cnic or "")
	if len(cnic) != 13:
		frappe.throw(frappe._("Donor CNIC must contain 13 digits."))

	return f"{cnic[:5]}-{cnic[5:12]}-{cnic[12]}"


def normalize_phone(phone_number):
	return re.sub(r"\D", "", phone_number or "")
