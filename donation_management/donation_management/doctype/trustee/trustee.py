# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.utils.nestedset import NestedSet


class Trustee(NestedSet):
	nsm_parent_field = "parent_trustee"

	def validate(self):
		self.normalize_cnic()
		self.validate_unique_cnic()
		self.normalize_old_membership_id()
		self.validate_unique_old_membership_id()
		self.set_contact_digits()
		self.validate_unique_contact()
		self.validate_contact_not_used_by_donor()
		self.validate_parent_trustee()

	def on_update(self):
		super().on_update()

	def normalize_cnic(self):
		if str(self.cnic or "").strip().startswith("-"):
			frappe.throw(frappe._("Trustee CNIC cannot be negative."))

		cnic_digits = normalize_digits(self.cnic)
		if cnic_digits and len(cnic_digits) != 13:
			frappe.throw(frappe._("Trustee CNIC must contain 13 digits."))

		self.cnic = cnic_digits or None

	def validate_unique_cnic(self):
		if not self.cnic:
			return

		existing_trustee = frappe.db.exists(
			"Trustee",
			{
				"cnic": self.cnic,
				"name": ["!=", self.name],
			},
		)
		if existing_trustee:
			frappe.throw(
				frappe._("Trustee CNIC {0} is already used by Trustee {1}.").format(
					self.cnic,
					existing_trustee,
				)
			)

	def normalize_old_membership_id(self):
		if self.old_membership_id:
			self.old_membership_id = self.old_membership_id.strip()
			if self.old_membership_id.startswith("-"):
				frappe.throw(frappe._("Old Membership ID cannot be negative."))

	def validate_unique_old_membership_id(self):
		if not self.old_membership_id:
			return

		existing_trustee = frappe.db.exists(
			"Trustee",
			{
				"old_membership_id": self.old_membership_id,
				"name": ["!=", self.name],
			},
		)
		if existing_trustee:
			frappe.throw(
				frappe._("Old Membership ID {0} is already used by Trustee {1}.").format(
					self.old_membership_id,
					existing_trustee,
				)
			)

	def set_contact_digits(self):
		self.contact_digits = normalize_phone(self.contact) or None

	def validate_unique_contact(self):
		if not self.contact_digits:
			return

		existing_trustee = find_trustee_by_phone_digits(self.contact_digits, exclude=self.name)
		if existing_trustee:
			frappe.throw(
				frappe._("Trustee Contact {0} is already used by Trustee {1}.").format(
					self.contact,
					existing_trustee,
				)
			)

	def validate_contact_not_used_by_donor(self):
		if not self.contact_digits:
			return

		existing_donor = find_donor_by_phone_digits(self.contact_digits)
		if existing_donor:
			frappe.throw(
				frappe._("Trustee Contact {0} is already used by Donor {1}.").format(
					self.contact,
					existing_donor,
				)
			)

	def validate_parent_trustee(self):
		if not self.parent_trustee:
			return

		if self.parent_trustee == self.name:
			frappe.throw(frappe._("Parent Trustee cannot be the same Trustee."))

		if not frappe.db.exists("Trustee", self.parent_trustee):
			frappe.throw(frappe._("Parent Trustee {0} was not found.").format(self.parent_trustee))

		if not frappe.db.get_value("Trustee", self.parent_trustee, "is_group"):
			frappe.throw(frappe._("Parent Trustee must be checked as Is Group."))

		parent = self.parent_trustee
		while parent:
			if parent == self.name:
				frappe.throw(frappe._("Circular Trustee hierarchy is not allowed."))

			parent = frappe.db.get_value("Trustee", parent, "parent_trustee")


def normalize_phone(phone_number):
	return normalize_digits(phone_number)


def normalize_digits(value):
	return re.sub(r"\D", "", value or "")


def find_trustee_by_phone_digits(phone_digits, exclude=None):
	if not phone_digits:
		return None

	trustee_meta = frappe.get_meta("Trustee")
	if trustee_meta.has_field("contact_digits"):
		existing_trustee = frappe.db.exists(
			"Trustee",
			{
				"contact_digits": phone_digits,
				"name": ["!=", exclude or ""],
			},
		)
		if existing_trustee:
			return existing_trustee

	for trustee in frappe.get_all(
		"Trustee",
		filters={"name": ["!=", exclude or ""]},
		fields=["name", "contact"],
	):
		if normalize_phone(trustee.contact) == phone_digits:
			return trustee.name

	return None


def find_donor_by_phone_digits(phone_digits):
	if not phone_digits or not frappe.db.table_exists("Donor"):
		return None

	donor_meta = frappe.get_meta("Donor")
	if donor_meta.has_field("donor_phone_digits"):
		existing_donor = frappe.db.exists("Donor", {"donor_phone_digits": phone_digits})
		if existing_donor:
			return existing_donor

	for donor in frappe.get_all("Donor", fields=["name", "donor_phone_number"]):
		if normalize_phone(donor.donor_phone_number) == phone_digits:
			return donor.name

	return None
