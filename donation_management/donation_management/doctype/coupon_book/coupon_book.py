# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, cint, flt, now_datetime, today

from donation_management.donation_management.api import (
	create_collection_journal_entry,
	set_collection_accounting_details,
	validate_collection_accounting_details,
)


COUPON_COLORS = {
	"Zakat": "Green",
	"Atiya": "Blue",
	"Fitra": "Purple",
	"Sadqa": "Orange",
}

DENOMINATIONS = (10, 20, 50, 100, 500, 1000, 5000)


class CouponBook(Document):
	def validate(self):
		self.set_defaults()
		self.validate_coupon_type()
		self.validate_status_transition()
		self.set_coupon_color()
		self.set_expiry_date()
		self.set_used_pages_from_coupons()
		self.set_remaining_pages()
		self.validate_page_counts()
		self.validate_stock_available_for_unissued_book()
		self.set_collected_amount_from_coupons()
		self.set_accounting_details()
		self.validate_cash_denominations()
		self.validate_accounting_details()
		self.validate_inventory_for_issue()

	def on_update(self):
		self.create_inventory_entry_for_status_change()
		self.create_journal_entry_for_return()

	def set_defaults(self):
		if not self.start_date:
			self.start_date = today()

	def validate_coupon_type(self):
		if self.coupon_type not in COUPON_COLORS:
			frappe.throw(frappe._("Coupon Type must be Zakat, Atiya, Fitra, or Sadqa."))

	def set_coupon_color(self):
		self.coupon_color = COUPON_COLORS.get(self.coupon_type)

	def set_expiry_date(self):
		if self.start_date:
			self.expiry_date = add_days(self.start_date, 45)

	def set_used_pages_from_coupons(self):
		if self.is_new():
			return

		self.used_pages = frappe.db.count("Coupon", {"coupon_book": self.name})

	def set_remaining_pages(self):
		self.remaining_pages = cint(self.total_pages) - cint(self.used_pages)

	def set_collected_amount_from_coupons(self):
		if self.status not in ("Returned", "Closed") or self.is_new():
			return

		self.collected_amount = get_coupon_book_collected_amount(self.name)

	def validate_status_transition(self):
		previous_status = self.get_previous_status()
		status = self.status or ""

		if not status:
			return

		if status not in ("Issued", "Returned", "Closed"):
			frappe.throw(frappe._("Status must be Issued, Returned, or Closed."))

		allowed_transitions = {
			None: ("Issued",),
			"": ("Issued",),
			"Issued": ("Returned",),
			"Returned": ("Closed",),
			"Closed": (),
		}

		if previous_status == status:
			return

		if status not in allowed_transitions.get(previous_status, ()):
			frappe.throw(
				frappe._("Coupon Book status cannot be changed from {0} to {1}.").format(
					previous_status or frappe._("Blank"),
					status,
				)
			)

	def validate_page_counts(self):
		if cint(self.total_pages) <= 0:
			frappe.throw(frappe._("Total Pages must be greater than zero."))
		if cint(self.used_pages) < 0:
			frappe.throw(frappe._("Used Pages cannot be negative."))
		if cint(self.used_pages) > cint(self.total_pages):
			frappe.throw(frappe._("Used Pages cannot exceed Total Pages."))

	def validate_stock_available_for_unissued_book(self):
		if self.status:
			return

		if not self.coupon_type or not self.warehouse:
			return

		available_quantity = get_available_coupon_book_stock(self.coupon_type, self.warehouse, self.name)
		if available_quantity <= 0:
			frappe.throw(
				frappe._("No unallocated Coupon Book stock is available for {0} in warehouse {1}.").format(
					self.coupon_type,
					self.warehouse,
				)
			)

	def validate_cash_denominations(self):
		if self.status in ("Returned", "Closed"):
			if flt(self.collected_amount) <= 0:
				frappe.throw(frappe._("Collected Amount is required when Coupon Book is returned."))
			if not self.cash_denominations:
				frappe.throw(frappe._("Cash Denominations are required when Coupon Book is returned."))

		if not self.cash_denominations and flt(self.collected_amount) <= 0:
			return

		denomination_total = 0
		has_note_count = False
		for row in self.cash_denominations:
			denomination = cint(row.denomination)
			if denomination not in DENOMINATIONS:
				frappe.throw(frappe._("Invalid denomination {0}.").format(row.denomination))

			if cint(row.note_count) < 0:
				frappe.throw(frappe._("Note count cannot be negative for denomination {0}.").format(row.denomination))

			row.amount = denomination * cint(row.note_count)
			denomination_total += flt(row.amount)
			if cint(row.note_count):
				has_note_count = True

		if flt(self.collected_amount) > 0 and not has_note_count:
			frappe.throw(frappe._("At least one denomination count is required."))

		if flt(self.collected_amount) != flt(denomination_total):
			frappe.throw(frappe._("Cash denomination total must match Collected Amount."))

	def set_accounting_details(self):
		if self.status not in ("Returned", "Closed"):
			return

		set_collection_accounting_details(self, "Coupon Book", self.coupon_type)

	def validate_accounting_details(self):
		if self.status not in ("Returned", "Closed"):
			return

		validate_collection_accounting_details(
			self,
			"Coupon Book",
			self.coupon_type,
			self.collected_amount,
		)

	def validate_inventory_for_issue(self):
		if self.status != "Issued" or self.get_previous_status() == "Issued":
			return

		if not self.warehouse:
			frappe.throw(frappe._("Warehouse is required before issuing a Coupon Book."))

		available_quantity = get_coupon_book_balance(self.coupon_type, self.warehouse)
		if available_quantity <= 0:
			frappe.throw(
				frappe._("No Coupon Book stock is available for {0} in warehouse {1}.").format(
					self.coupon_type,
					self.warehouse,
				)
			)

	def create_inventory_entry_for_status_change(self):
		previous_status = self.get_previous_status()
		if previous_status == self.status:
			return

		if self.status == "Issued":
			self.create_inventory_entry("Issue", -1)

	def create_journal_entry_for_return(self):
		if self.status != "Returned":
			return

		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			return

		create_collection_journal_entry(
			self,
			source_type="Coupon Book",
			donation_type=self.coupon_type,
			amount=self.collected_amount,
			posting_date=today(),
			remarks=self.get_collection_accounting_remarks(),
			received_from=self.get_collection_received_from(),
		)

	def get_previous_status(self):
		previous_doc = self.get_doc_before_save()
		return previous_doc.status if previous_doc else None

	def create_inventory_entry(self, movement_type, signed_quantity):
		if not frappe.db.table_exists("Coupon Book Inventory"):
			return

		frappe.get_doc(
			{
				"doctype": "Coupon Book Inventory",
				"posting_date": now_datetime(),
				"coupon_type": self.coupon_type,
				"warehouse": self.warehouse,
				"movement_type": movement_type,
				"quantity": abs(cint(signed_quantity)),
				"signed_quantity": cint(signed_quantity),
				"volunteer_name": self.volunteer_name,
			}
		).insert(ignore_permissions=True)

	def get_collection_accounting_remarks(self):
		return "Coupon Book: {0} | Coupon Type: {1} | Warehouse: {2} | Volunteer: {3}".format(
			self.name,
			self.coupon_type,
			self.warehouse,
			self.volunteer_name or "",
		)

	def get_collection_received_from(self):
		return "Coupon Book {0} ({1})".format(self.name, self.coupon_type)


@frappe.whitelist()
def issue_coupon_book(coupon_book):
	doc = frappe.get_doc("Coupon Book", coupon_book)
	if doc.status:
		frappe.throw(frappe._("Only unissued Coupon Books can be issued."))

	doc.status = "Issued"
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def return_coupon_book(
	coupon_book,
	collected_amount=None,
	denominations=None,
	mode_of_payment=None,
	debit_account=None,
	credit_account=None,
):
	doc = frappe.get_doc("Coupon Book", coupon_book)
	if doc.status != "Issued":
		frappe.throw(frappe._("Only issued Coupon Books can be returned."))

	denominations = frappe.parse_json(denominations) or []
	doc.set("cash_denominations", [])
	for row in denominations:
		if cint(row.get("note_count")):
			doc.append(
				"cash_denominations",
				{
					"denomination": cint(row.get("denomination")),
					"note_count": cint(row.get("note_count")),
				},
			)

	doc.collected_amount = get_coupon_book_collected_amount(coupon_book)
	doc.mode_of_payment = mode_of_payment or doc.mode_of_payment
	doc.debit_account = debit_account or doc.debit_account
	doc.credit_account = credit_account or doc.credit_account
	doc.status = "Returned"
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def get_coupon_book_collected_amount(coupon_book):
	if not coupon_book:
		return 0

	return flt(
		frappe.db.get_value(
			"Coupon",
			{
				"coupon_book": coupon_book,
				"docstatus": ["!=", 2],
			},
			"sum(amount)",
		)
	)


@frappe.whitelist()
def close_coupon_book(coupon_book):
	doc = frappe.get_doc("Coupon Book", coupon_book)
	if doc.status != "Returned":
		frappe.throw(frappe._("Only returned Coupon Books can be closed."))

	doc.status = "Closed"
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def get_available_coupon_book_stock(coupon_type, warehouse, exclude_coupon_book=None):
	if not coupon_type or not warehouse:
		return 0

	total_stock = get_total_coupon_book_stock(coupon_type, warehouse)
	created_books = get_created_coupon_book_count(coupon_type, warehouse, exclude_coupon_book)
	return max(total_stock - created_books, 0)


def get_total_coupon_book_stock(coupon_type, warehouse):
	if not frappe.db.table_exists("Coupon Book Inventory"):
		return 0

	return cint(
		frappe.db.get_value(
			"Coupon Book Inventory",
			{
				"coupon_type": coupon_type,
				"warehouse": warehouse,
				"movement_type": "Receipt",
				"docstatus": ["!=", 2],
			},
			"sum(quantity)",
		)
	)


def get_created_coupon_book_count(coupon_type, warehouse, exclude_coupon_book=None):
	filters = {
		"coupon_type": coupon_type,
		"warehouse": warehouse,
		"docstatus": ["!=", 2],
	}
	if exclude_coupon_book:
		filters["name"] = ["!=", exclude_coupon_book]

	return cint(frappe.db.count("Coupon Book", filters))


def get_coupon_book_balance(coupon_type, warehouse):
	if not frappe.db.table_exists("Coupon Book Inventory"):
		return 0

	return cint(
		frappe.db.get_value(
			"Coupon Book Inventory",
			{
				"coupon_type": coupon_type,
				"warehouse": warehouse,
				"docstatus": ["!=", 2],
			},
			"sum(signed_quantity)",
		)
	)
