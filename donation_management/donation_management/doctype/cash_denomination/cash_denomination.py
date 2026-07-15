# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint


DENOMINATIONS = (10, 20, 50, 100, 500, 1000, 5000)


class CashDenomination(Document):
	def validate(self):
		denomination = cint(self.denomination)
		if denomination not in DENOMINATIONS:
			frappe.throw(frappe._("Invalid denomination {0}.").format(self.denomination))

		note_count = cint(self.note_count)
		if note_count < 0:
			frappe.throw(frappe._("Note count cannot be negative for denomination {0}.").format(self.denomination))

		self.amount = denomination * note_count
