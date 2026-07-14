# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, now_datetime


class BookPageAdjustment(Document):
	def validate(self):
		self.validate_book()
		self.validate_affected_pages()

	def on_submit(self):
		if self.status == "Draft":
			self.status = "Pending Donation Manager"
			self.db_set("status", self.status, update_modified=False)

	def validate_book(self):
		if not self.book:
			return

		book_details = frappe.db.get_value("Book", self.book, ["book_type", "status"], as_dict=True)
		if not book_details or book_details.book_type != "Coupon Book":
			frappe.throw(frappe._("Page adjustments can only be requested for Coupon Book records."))

		if book_details.status not in ("Issued", "Returned", "Closed"):
			frappe.throw(
				frappe._("Page adjustments can only be requested for Issued, Returned, or Closed coupon books.")
			)

	def validate_affected_pages(self):
		if cint(self.affected_pages) <= 0:
			frappe.throw(frappe._("Affected Pages must be greater than zero."))

		if not self.book:
			return

		total_pages = cint(frappe.db.get_value("Book", self.book, "total_pages"))
		if cint(self.affected_pages) > total_pages:
			frappe.throw(
				frappe._("Affected Pages ({0}) cannot exceed Total Pages ({1}).").format(
					self.affected_pages,
					total_pages,
				)
			)

	@frappe.whitelist()
	def approve_by_donation_manager(self):
		self.validate_permission("Donation Manager")
		if self.status != "Pending Donation Manager":
			frappe.throw(frappe._("Only requests pending Donation Manager approval can be approved at this stage."))

		self.status = "Pending Finance Manager"
		self.donation_manager = frappe.session.user
		self.donation_manager_approved_on = now_datetime()
		self.save(ignore_permissions=True)
		return self.status

	@frappe.whitelist()
	def reject_request(self):
		self.validate_permission(["Donation Manager", "Finance Manager"])
		if self.status not in ("Pending Donation Manager", "Pending Finance Manager"):
			frappe.throw(frappe._("Only pending requests can be rejected."))

		self.status = "Rejected"
		self.save(ignore_permissions=True)
		return self.status

	@frappe.whitelist()
	def approve_by_finance_manager(self):
		self.validate_permission(["Finance Manager", "System Manager"])
		if self.status != "Pending Finance Manager":
			frappe.throw(frappe._("Only requests pending Finance Manager approval can be approved at this stage."))

		self.status = "Approved"
		self.finance_manager = frappe.session.user
		self.finance_manager_approved_on = now_datetime()
		self.save(ignore_permissions=True)
		self.apply_adjustment_to_book()
		return self.status

	def apply_adjustment_to_book(self):
		book = frappe.get_doc("Book", self.book)
		affected = cint(self.affected_pages)

		if self.adjustment_type == "Less Pages or Leaves":
			new_total = max(cint(book.total_pages) - affected, cint(book.used_pages))
			book.total_pages = new_total
		else:
			book.total_pages = max(cint(book.total_pages) - affected, cint(book.used_pages))

		book.remaining_pages = max(cint(book.total_pages) - cint(book.used_pages), 0)
		book.flags.ignore_validate = True
		book.save(ignore_permissions=True)

	def validate_permission(self, roles):
		if isinstance(roles, str):
			roles = [roles]

		if "System Manager" in frappe.get_roles():
			return

		user_roles = set(frappe.get_roles())
		if not user_roles.intersection(set(roles)):
			frappe.throw(frappe._("You do not have permission to perform this action."))
