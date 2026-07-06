# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, getdate, now_datetime

from donation_management.donation_management.api import get_default_cash_account, get_default_company


class DonationClosing(Document):
	def validate(self):
		self.set_company_default()
		self.set_totals()
		self.validate_closing_details()

	def on_submit(self):
		if not self.closing_details:
			frappe.throw(frappe._("Add at least one pending cash donation before submitting."))

		self.status = "Submitted"
		self.db_set("status", self.status, update_modified=False)
		self.notify_finance_team()

	def on_cancel(self):
		self.status = "Cancelled"
		self.db_set("status", self.status, update_modified=False)
		if self.journal_entry:
			self.cancel_bank_journal_entry()
		self.reset_source_deposit_status()

	def set_company_default(self):
		if not self.company:
			self.company = get_default_company()

	def set_totals(self):
		self.total_amount = sum(flt(row.amount) for row in self.closing_details or [])
		self.pending_items_count = len(self.closing_details or [])

	def validate_closing_details(self):
		seen = set()
		for row in self.closing_details or []:
			key = (row.source_doctype, row.source_name)
			if key in seen:
				frappe.throw(
					frappe._("Duplicate entry for {0} {1}.").format(row.source_doctype, row.source_name)
				)
			seen.add(key)

			if is_source_in_active_closing(row.source_doctype, row.source_name, exclude=self.name):
				frappe.throw(
					frappe._("{0} {1} is already included in another active Donation Closing.").format(
						row.source_doctype,
						row.source_name,
					)
				)

	@frappe.whitelist()
	def fetch_pending_cash_donations(self):
		self.set_company_default()
		pending = get_pending_cash_donations(self.company, exclude_closing=self.name)
		self.closing_details = []

		for item in pending:
			posting_date = item.get("posting_date")
			if posting_date:
				posting_date = getdate(posting_date)

			self.append(
				"closing_details",
				{
					"source_doctype": item["source_doctype"],
					"source_name": item["source_name"],
					"donation_type": item.get("donation_type"),
					"amount": item.get("amount"),
					"posting_date": posting_date,
					"remarks": item.get("remarks"),
				},
			)

		self.set_totals()

		if not pending:
			return {
				"count": 0,
				"total_amount": 0,
				"message": frappe._(
					"No pending cash donations were found for {0}. "
					"Cash Donation Orders must be submitted with Posted accounting and "
					"Bank Deposit Status Pending Bank Deposit. Box Collections must be Collected "
					"and Coupon Books must be Returned/Closed with Posted accounting."
				).format(self.company),
			}

		self.save()
		return {
			"count": self.pending_items_count,
			"total_amount": self.total_amount,
			"name": self.name,
			"closing_details": get_closing_details_payload(self),
		}

	@frappe.whitelist()
	def submit_bank_deposit(self, bank_deposit_date=None, bank_deposit_reference=None, bank_account=None):
		self.validate_finance_permission()
		if self.docstatus != 1 or self.status not in ("Submitted", "Pending Bank Deposit"):
			frappe.throw(frappe._("Only submitted closings pending bank deposit can be processed."))

		if bank_deposit_date:
			self.bank_deposit_date = bank_deposit_date
		if bank_deposit_reference:
			self.bank_deposit_reference = bank_deposit_reference
		if bank_account:
			self.bank_account = bank_account

		if not self.bank_deposit_date:
			frappe.throw(frappe._("Cash Deposit Slip Date is required."))
		if not self.bank_account:
			frappe.throw(frappe._("Bank Account is required."))

		self.validate_bank_account()
		self.create_bank_journal_entry()
		self.status = "Bank Deposited"
		self.deposited_by = frappe.session.user
		self.deposited_on = now_datetime()
		self.accounting_status = "Posted"
		self.save(ignore_permissions=True)
		self.mark_sources_as_deposited()
		return self.name

	def mark_sources_as_deposited(self):
		for row in self.closing_details or []:
			if row.source_doctype == "Donation Order" and frappe.db.has_column(
				"Donation Order", "bank_deposit_status"
			):
				frappe.db.set_value(
					"Donation Order",
					row.source_name,
					"bank_deposit_status",
					"Deposited",
					update_modified=False,
				)

	def reset_source_deposit_status(self):
		for row in self.closing_details or []:
			if row.source_doctype != "Donation Order":
				continue

			if frappe.db.get_value("Donation Order", row.source_name, "bank_deposit_status") == "Deposited":
				frappe.db.set_value(
					"Donation Order",
					row.source_name,
					"bank_deposit_status",
					"Pending Bank Deposit",
					update_modified=False,
				)

	def validate_bank_account(self):
		account_details = frappe.db.get_value(
			"Account",
			self.bank_account,
			["company", "is_group", "account_type"],
			as_dict=True,
		)
		if not account_details:
			frappe.throw(frappe._("Bank Account {0} was not found.").format(self.bank_account))
		if account_details.company != self.company:
			frappe.throw(frappe._("Bank Account must belong to Company {0}.").format(self.company))
		if account_details.is_group:
			frappe.throw(frappe._("Bank Account cannot be a group account."))
		if account_details.account_type != "Bank":
			frappe.throw(frappe._("Bank Account must be a Bank type account."))

	def create_bank_journal_entry(self):
		if self.journal_entry and frappe.db.exists("Journal Entry", self.journal_entry):
			if frappe.db.get_value("Journal Entry", self.journal_entry, "docstatus") == 1:
				return
			frappe.throw(
				frappe._("Linked Journal Entry {0} is not submitted.").format(self.journal_entry)
			)

		cash_account = get_default_cash_account(self.company)
		if not cash_account:
			frappe.throw(frappe._("Default Cash Account was not found for Company {0}.").format(self.company))

		cost_center = frappe.db.get_value("Company", self.company, "cost_center")
		amount = flt(self.total_amount)
		remarks = "Donation Closing {0} | Ref: {1}".format(
			self.name,
			self.bank_deposit_reference or "",
		)

		entry = frappe.get_doc(
			{
				"doctype": "Journal Entry",
				"voucher_type": "Journal Entry",
				"company": self.company,
				"posting_date": getdate(self.bank_deposit_date),
				"user_remark": remarks,
				"accounts": [
					{
						"account": self.bank_account,
						"debit_in_account_currency": amount,
						"credit_in_account_currency": 0,
						"cost_center": cost_center,
					},
					{
						"account": cash_account,
						"debit_in_account_currency": 0,
						"credit_in_account_currency": amount,
						"cost_center": cost_center,
					},
				],
			}
		)
		entry.insert(ignore_permissions=True)
		entry.submit()
		self.journal_entry = entry.name

	def cancel_bank_journal_entry(self):
		if not self.journal_entry:
			return

		je = frappe.get_doc("Journal Entry", self.journal_entry)
		if je.docstatus == 1:
			je.cancel()
		self.accounting_status = "Cancelled"
		self.db_set("accounting_status", self.accounting_status, update_modified=False)

	def notify_finance_team(self):
		recipients = get_finance_notification_recipients()
		if not recipients:
			return

		subject = frappe._("Donation Closing {0} submitted for bank deposit").format(self.name)
		message = frappe._(
			"Donation Closing {0} for {1} has been submitted with total amount {2}. "
			"Please review and record the bank deposit details."
		).format(
			self.name,
			frappe.format_value(self.closing_date, {"fieldtype": "Date"}),
			frappe.format_value(self.total_amount, {"fieldtype": "Currency"}),
		)

		frappe.sendmail(recipients=recipients, subject=subject, message=message)

	def validate_finance_permission(self):
		allowed_roles = {"Finance Manager", "CFO", "System Manager"}
		if not allowed_roles.intersection(set(frappe.get_roles())):
			frappe.throw(frappe._("Only Finance Manager or CFO can record bank deposit details."))


def get_finance_notification_recipients():
	roles = ["Finance Manager", "CFO"]
	recipients = set()
	for role in roles:
		for user in frappe.get_all("Has Role", filters={"role": role, "parenttype": "User"}, pluck="parent"):
			recipients.add(user)
	return list(recipients)


def get_closing_details_payload(doc):
	return [
		{
			"source_doctype": row.source_doctype,
			"source_name": row.source_name,
			"donation_type": row.donation_type,
			"amount": row.amount,
			"posting_date": row.posting_date,
			"remarks": row.remarks,
		}
		for row in doc.closing_details or []
	]


def get_pending_cash_donations(company=None, exclude_closing=None):
	company = company or get_default_company()
	pending = []
	pending.extend(get_pending_donation_orders(company, exclude_closing))
	pending.extend(get_pending_box_collections(company, exclude_closing))
	pending.extend(get_pending_coupon_books(company, exclude_closing))
	return pending


def get_pending_donation_orders(company, exclude_closing=None):
	orders = frappe.get_all(
		"Donation Order",
		filters={
			"docstatus": 1,
			"company": company,
			"mode_of_payment_type": "Cash",
			"accounting_status": "Posted",
		},
		fields=[
			"name",
			"donation_amount",
			"donation_type",
			"donation_posting_date",
			"bank_deposit_status",
		],
		order_by="donation_posting_date asc",
	)

	result = []
	for order in orders:
		deposit_status = order.bank_deposit_status or "Not Applicable"
		if deposit_status == "Deposited":
			continue

		if is_source_in_active_closing("Donation Order", order.name, exclude=exclude_closing):
			continue

		result.append(
			{
				"source_doctype": "Donation Order",
				"source_name": order.name,
				"donation_type": order.donation_type,
				"amount": order.donation_amount,
				"posting_date": getdate(order.donation_posting_date)
				if order.donation_posting_date
				else None,
				"remarks": order.name,
			}
		)
	return result


def get_pending_box_collections(company, exclude_closing=None):
	collections = frappe.db.sql(
		"""
		select
			collection_log.name,
			collection_log.box_collection,
			collection_log.collected_amount,
			collection_log.donation_head,
			collection_log.action_date,
			collection_log.journal_entry
		from `tabBox Collection Log` collection_log
		inner join `tabBox Collection` box_collection
			on box_collection.name = collection_log.box_collection
		inner join `tabJournal Entry` journal_entry
			on journal_entry.name = collection_log.journal_entry
			and journal_entry.docstatus = 1
		where box_collection.docstatus = 1
			and box_collection.company = %(company)s
			and collection_log.action = 'Collection'
			and ifnull(collection_log.collected_amount, 0) > 0
			and not exists (
				select 1
				from `tabBox Collection Log` newer_log
				where newer_log.box_collection = collection_log.box_collection
					and newer_log.action = 'Collection'
					and (
						newer_log.action_date > collection_log.action_date
						or (
							newer_log.action_date = collection_log.action_date
							and newer_log.creation > collection_log.creation
						)
					)
			)
		order by collection_log.action_date asc, collection_log.creation asc
		""",
		{"company": company},
		as_dict=True,
	)

	result = []
	for collection in collections:
		if is_source_in_active_closing("Box Collection Log", collection.name, exclude=exclude_closing):
			continue
		result.append(
			{
				"source_doctype": "Box Collection Log",
				"source_name": collection.name,
				"donation_type": collection.donation_head,
				"amount": collection.collected_amount,
				"posting_date": getdate(collection.action_date),
				"remarks": "{0} | {1}".format(collection.box_collection, collection.name),
			}
		)
	return result


def get_pending_coupon_books(company, exclude_closing=None):
	books = frappe.get_all(
		"Coupon Book",
		filters={
			"status": ["in", ["Returned", "Closed"]],
			"company": company,
			"accounting_status": "Posted",
		},
		fields=["name", "collected_amount", "coupon_type", "start_date"],
		order_by="start_date asc",
	)

	result = []
	for book in books:
		if is_source_in_active_closing("Coupon Book", book.name, exclude=exclude_closing):
			continue
		result.append(
			{
				"source_doctype": "Coupon Book",
				"source_name": book.name,
				"donation_type": book.coupon_type,
				"amount": book.collected_amount,
				"posting_date": book.start_date,
				"remarks": book.name,
			}
		)
	return result


def is_source_in_active_closing(source_doctype, source_name, exclude=None):
	filters = {
		"parenttype": "Donation Closing",
		"source_doctype": source_doctype,
		"source_name": source_name,
	}
	rows = frappe.get_all("Donation Closing Detail", filters=filters, fields=["parent"])
	for row in rows:
		closing_status = frappe.db.get_value("Donation Closing", row.parent, ["docstatus", "status"], as_dict=True)
		if not closing_status:
			continue
		if exclude and row.parent == exclude:
			continue
		if closing_status.docstatus == 1 and closing_status.status not in ("Cancelled",):
			return True
	return False
