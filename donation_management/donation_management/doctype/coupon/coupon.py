# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import cint


COUPON_COLORS = {
	"Zakat": "Green",
	"Atiya": "Blue",
	"Fitra": "Purple",
	"Sadqa": "Orange",
}

COUPON_SERIES = {
	"Zakat": "ZKT-.#####",
	"Atiya": "ATI-.#####",
	"Fitra": "FTR-.#####",
	"Sadqa": "SDQ-.#####",
}


class Coupon(Document):
	def before_insert(self):
		self.set_coupon_number()

	def validate(self):
		self.set_coupon_book_details()
		self.validate_coupon_book_page_available()
		self.set_coupon_color()
		if not self.coupon_number:
			self.set_coupon_number()

	def on_update(self):
		previous_doc = self.get_doc_before_save()
		if previous_doc and previous_doc.coupon_book and previous_doc.coupon_book != self.coupon_book:
			sync_coupon_book_page_counts(previous_doc.coupon_book)

		self.sync_coupon_book_pages()

	def on_trash(self):
		if self.coupon_book:
			sync_coupon_book_page_counts(self.coupon_book, exclude_coupon=self.name)

	def set_coupon_book_details(self):
		if not self.coupon_book:
			frappe.throw(frappe._("Coupon Book is required."))

		coupon_book = frappe.db.get_value(
			"Coupon Book",
			self.coupon_book,
			["coupon_type", "coupon_color", "volunteer_name", "warehouse", "status"],
			as_dict=True,
		)
		if not coupon_book:
			frappe.throw(frappe._("Coupon Book {0} was not found.").format(self.coupon_book))

		if coupon_book.status != "Issued":
			frappe.throw(frappe._("Coupon Book {0} must be Issued before creating a Coupon.").format(self.coupon_book))

		self.coupon_color = coupon_book.coupon_color
		self.volunteer_name = coupon_book.volunteer_name
		self.warehouse = coupon_book.warehouse

		return coupon_book

	def validate_coupon_book_page_available(self):
		if not self.coupon_book:
			return

		coupon_book = frappe.db.get_value(
			"Coupon Book",
			self.coupon_book,
			["total_pages", "remaining_pages"],
			as_dict=True,
		)
		if not coupon_book:
			return

		is_existing_coupon = not self.is_new() and frappe.db.exists(
			"Coupon",
			{
				"name": self.name,
				"coupon_book": self.coupon_book,
			},
		)
		used_coupon_count = get_used_coupon_count(
			self.coupon_book,
			exclude_coupon=self.name if is_existing_coupon else None,
		)

		if used_coupon_count >= cint(coupon_book.total_pages) or (
			cint(coupon_book.remaining_pages) <= 0 and not is_existing_coupon
		):
			frappe.throw(
				frappe._("All pages are used for Coupon Book {0}. New Coupon cannot be created.").format(
					self.coupon_book,
				)
			)

	def sync_coupon_book_pages(self):
		if not self.coupon_book:
			return

		sync_coupon_book_page_counts(self.coupon_book)

	def set_coupon_color(self):
		coupon_type = self.get_coupon_type()
		self.coupon_color = COUPON_COLORS.get(coupon_type)

	def set_coupon_number(self):
		coupon_type = self.get_coupon_type()
		self.coupon_number = make_autoname(COUPON_SERIES[coupon_type])

	def get_coupon_type(self):
		if not self.coupon_book:
			frappe.throw(frappe._("Coupon Book is required before generating Coupon Number."))

		coupon_type = frappe.db.get_value("Coupon Book", self.coupon_book, "coupon_type")
		if coupon_type not in COUPON_COLORS:
			frappe.throw(frappe._("Coupon Book Type must be Zakat, Atiya, Fitra, or Sadqa."))

		return coupon_type


def get_used_coupon_count(coupon_book, exclude_coupon=None):
	filters = {
		"coupon_book": coupon_book,
	}
	if exclude_coupon:
		filters["name"] = ["!=", exclude_coupon]

	return frappe.db.count("Coupon", filters)


def sync_coupon_book_page_counts(coupon_book, exclude_coupon=None):
	total_pages = frappe.db.get_value("Coupon Book", coupon_book, "total_pages")
	if total_pages is None:
		return

	used_pages = get_used_coupon_count(coupon_book, exclude_coupon=exclude_coupon)
	remaining_pages = max(cint(total_pages) - used_pages, 0)
	frappe.db.set_value(
		"Coupon Book",
		coupon_book,
		{
			"used_pages": used_pages,
			"remaining_pages": remaining_pages,
		},
		update_modified=False,
	)
