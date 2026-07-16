import frappe


def execute():
	from donation_management.donation_management.doctype.book.book import (
		BOOK_TYPE_DONATION,
		update_donation_book_receipt_usage,
	)

	for book in frappe.get_all("Book", filters={"book_type": BOOK_TYPE_DONATION}, pluck="name"):
		update_donation_book_receipt_usage(book)
