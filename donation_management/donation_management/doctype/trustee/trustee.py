# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils.nestedset import NestedSet


class Trustee(NestedSet):
	nsm_parent_field = "parent_trustee"

	def validate(self):
		self.validate_parent_trustee()

	def on_update(self):
		super().on_update()

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
