# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


MOVEMENT_SIGNS = {
	"Receipt": 1,
	"Issue": -1,
	"Return": 1,
}


class CouponBookInventory(Document):
	def validate(self):
		self.set_defaults()
		self.validate_quantity()
		self.set_signed_quantity()

	def set_defaults(self):
		if not self.posting_date:
			self.posting_date = now_datetime()
		if not self.movement_type:
			self.movement_type = "Receipt"

	def validate_quantity(self):
		if cint(self.quantity) <= 0:
			frappe.throw(frappe._("Quantity must be greater than zero."))

	def set_signed_quantity(self):
		if self.movement_type not in MOVEMENT_SIGNS:
			frappe.throw(frappe._("Invalid Movement Type."))

		self.signed_quantity = MOVEMENT_SIGNS[self.movement_type] * cint(self.quantity)
