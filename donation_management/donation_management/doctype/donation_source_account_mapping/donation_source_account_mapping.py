# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DonationSourceAccountMapping(Document):
	def validate(self):
		self.validate_unique_mapping()
		self.validate_credit_account()
		self.validate_cost_center()

	def validate_unique_mapping(self):
		existing = frappe.db.exists(
			"Donation Source Account Mapping",
			{
				"company": self.company,
				"source_type": self.source_type,
				"donation_type": self.donation_type,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(
				frappe._("Mapping already exists for {0}, {1}, and {2}.").format(
					self.company,
					self.source_type,
					self.donation_type,
				)
			)

	def validate_credit_account(self):
		account = frappe.db.get_value(
			"Account",
			self.credit_account,
			["name", "company", "is_group", "root_type"],
			as_dict=True,
		)
		if not account:
			frappe.throw(frappe._("Credit Account {0} was not found.").format(self.credit_account))

		if account.company != self.company:
			frappe.throw(
				frappe._("Credit Account {0} does not belong to Company {1}.").format(
					self.credit_account,
					self.company,
				)
			)

		if account.is_group:
			frappe.throw(frappe._("Credit Account {0} cannot be a group account.").format(self.credit_account))

		if account.root_type not in ("Income", "Liability", "Equity"):
			frappe.throw(
				frappe._("Credit Account {0} must be an Income, Liability, or Equity account.").format(
					self.credit_account
				)
			)

	def validate_cost_center(self):
		if not self.cost_center:
			return

		cost_center = frappe.db.get_value(
			"Cost Center",
			self.cost_center,
			["name", "company", "is_group"],
			as_dict=True,
		)
		if not cost_center:
			frappe.throw(frappe._("Cost Center {0} was not found.").format(self.cost_center))

		if cost_center.company != self.company:
			frappe.throw(
				frappe._("Cost Center {0} does not belong to Company {1}.").format(
					self.cost_center,
					self.company,
				)
			)

		if cost_center.is_group:
			frappe.throw(frappe._("Cost Center {0} cannot be a group cost center.").format(self.cost_center))
