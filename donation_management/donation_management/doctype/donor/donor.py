# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import re

import frappe
from frappe.utils import cint
from frappe.utils.nestedset import NestedSet


VALID_DONOR_TYPES = ("Walk-in", "Refered by Trustee")
DONOR_BRANCH = "Branch:Donor"
TRUSTEE_BRANCH = "Branch:Refered by Trustee"
DONOR_NODE_PREFIX = "Donor:"
TRUSTEE_NODE_PREFIX = "Trustee:"


class Donor(NestedSet):
	nsm_parent_field = "parent_donor"

	def validate(self):
		self.set_donor_type()
		self.set_trustee_reference()
		self.validate_parent_donor()
		self.set_donor_cnic()
		self.set_donor_phone_digits()
		self.validate_unique_donor_cnic()
		self.validate_unique_donor_phone()

	def on_update(self):
		super().on_update()

	def set_donor_type(self):
		if self.customer_type not in VALID_DONOR_TYPES:
			self.customer_type = "Walk-in"

	def set_trustee_reference(self):
		if self.customer_type == "Walk-in":
			self.referred_by_trustee = None
			return

		self.parent_donor = None

		if not self.referred_by_trustee:
			frappe.throw(frappe._("Referred By Trustee is required."))

		if self.referred_by_trustee == self.name:
			frappe.throw(frappe._("Referred By Trustee cannot refer to the same Donor."))

		trustee = frappe.db.exists("Trustee", self.referred_by_trustee)
		if not trustee:
			frappe.throw(frappe._("Referred By Trustee {0} was not found.").format(self.referred_by_trustee))

		if not frappe.db.get_value("Trustee", self.referred_by_trustee, "is_group"):
			frappe.throw(frappe._("Referred By Trustee must be checked as Is Group."))

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

	def validate_parent_donor(self):
		if not self.parent_donor:
			return

		if self.parent_donor == self.name:
			frappe.throw(frappe._("Parent Donor cannot be the same Donor."))

		if not frappe.db.exists("Donor", self.parent_donor):
			frappe.throw(frappe._("Parent Donor {0} was not found.").format(self.parent_donor))

		if not frappe.db.get_value("Donor", self.parent_donor, "is_group"):
			frappe.throw(frappe._("Parent Donor must be checked as Is Group."))

		parent = self.parent_donor
		while parent:
			if parent == self.name:
				frappe.throw(frappe._("Circular Donor hierarchy is not allowed."))

			parent = frappe.db.get_value("Donor", parent, "parent_donor")


def normalize_cnic(cnic):
	cnic = re.sub(r"\D", "", cnic or "")
	if len(cnic) != 13:
		frappe.throw(frappe._("Donor CNIC must contain 13 digits."))

	return f"{cnic[:5]}-{cnic[5:12]}-{cnic[12]}"


def normalize_phone(phone_number):
	return re.sub(r"\D", "", phone_number or "")


@frappe.whitelist()
def get_referral_tree_children(doctype, parent=None, **kwargs):
	frappe.has_permission("Donor", "read", throw=True)
	frappe.has_permission("Trustee", "read", throw=True)

	if not parent or parent == "Donations":
		return [
			{
				"value": DONOR_BRANCH,
				"title": frappe._("Donor"),
				"expandable": _has_donor_branch_nodes(),
				"hide_open": True,
			},
			{
				"value": TRUSTEE_BRANCH,
				"title": frappe._("Refered by Trustee"),
				"expandable": _has_trustee_branch_nodes(),
				"hide_open": True,
			},
		]

	if parent == DONOR_BRANCH:
		return _get_donor_nodes([["ifnull(parent_donor, '')", "=", ""], ["ifnull(referred_by_trustee, '')", "=", ""]])

	if parent == TRUSTEE_BRANCH:
		return _get_top_level_trustee_nodes()

	if parent.startswith(DONOR_NODE_PREFIX):
		return _get_child_donor_nodes(parent[len(DONOR_NODE_PREFIX) :])

	if parent.startswith(TRUSTEE_NODE_PREFIX):
		return _get_trustee_children(parent[len(TRUSTEE_NODE_PREFIX) :])

	return []


def _has_donor_branch_nodes():
	return _exists(
		"Donor",
		[["ifnull(parent_donor, '')", "=", ""], ["ifnull(referred_by_trustee, '')", "=", ""]],
	)


def _has_trustee_branch_nodes():
	return _exists("Trustee", [["ifnull(parent_trustee, '')", "=", ""], ["is_group", "=", 1]])


def _get_child_donor_nodes(parent_donor):
	return _get_donor_nodes([["parent_donor", "=", parent_donor], ["ifnull(referred_by_trustee, '')", "=", ""]])


def _get_donor_nodes(filters):
	donors = frappe.get_list(
		"Donor",
		filters=filters,
		fields=["name", "customer_name", "is_group"],
		order_by="customer_name asc, name asc",
	)

	return [
		{
			"value": f"{DONOR_NODE_PREFIX}{donor.name}",
			"title": donor.customer_name or donor.name,
			"expandable": cint(donor.is_group) or _donor_has_children(donor.name),
			"is_group": cint(donor.is_group),
			"reference_doctype": "Donor",
			"reference_name": donor.name,
		}
		for donor in donors
	]


def _donor_has_children(donor):
	return _exists("Donor", [["parent_donor", "=", donor], ["ifnull(referred_by_trustee, '')", "=", ""]])


def _get_top_level_trustee_nodes():
	return _get_trustee_nodes([["ifnull(parent_trustee, '')", "=", ""], ["is_group", "=", 1]])


def _get_trustee_children(trustee):
	nodes = _get_trustee_nodes({"parent_trustee": trustee, "is_group": 1})
	nodes.extend(_get_referred_donor_nodes(trustee))
	return nodes


def _get_trustee_nodes(filters):
	trustees = frappe.get_list(
		"Trustee",
		filters=filters,
		fields=["name", "trustee_name"],
		order_by="trustee_name asc, name asc",
	)

	return [
		{
			"value": f"{TRUSTEE_NODE_PREFIX}{trustee.name}",
			"title": trustee.trustee_name or trustee.name,
			"expandable": _trustee_has_children(trustee.name),
			"reference_doctype": "Trustee",
			"reference_name": trustee.name,
		}
		for trustee in trustees
	]


def _get_referred_donor_nodes(trustee):
	donors = frappe.get_list(
		"Donor",
		filters={"referred_by_trustee": trustee},
		fields=["name", "customer_name", "is_group"],
		order_by="customer_name asc, name asc",
	)

	return [
		{
			"value": f"{DONOR_NODE_PREFIX}{donor.name}",
			"title": donor.customer_name or donor.name,
			"expandable": cint(donor.is_group) or _donor_has_children(donor.name),
			"is_group": cint(donor.is_group),
			"reference_doctype": "Donor",
			"reference_name": donor.name,
		}
		for donor in donors
	]


def _trustee_has_children(trustee):
	return bool(
		frappe.db.exists("Trustee", {"parent_trustee": trustee, "is_group": 1})
		or frappe.db.exists("Donor", {"referred_by_trustee": trustee})
	)


def _exists(doctype, filters):
	return bool(frappe.get_all(doctype, filters=filters, pluck="name", limit=1))
