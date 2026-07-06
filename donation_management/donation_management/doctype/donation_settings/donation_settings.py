# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


class DonationSettings(Document):
	pass


def allow_donor_without_phone_or_email():
	return cint(frappe.db.get_single_value("Donation Settings", "allow_donor_without_phone_or_email"))


def is_donor_contact_required():
	return not allow_donor_without_phone_or_email()


def allow_duplicate_donor_phone():
	return cint(frappe.db.get_single_value("Donation Settings", "allow_duplicate_donor_phone"))


def is_duplicate_donor_phone_allowed():
	return allow_duplicate_donor_phone()
