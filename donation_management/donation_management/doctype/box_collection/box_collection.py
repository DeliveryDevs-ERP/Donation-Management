# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import cint, flt, now_datetime, today

from donation_management.donation_management.api import (
	create_collection_journal_entry,
	set_collection_accounting_details,
	validate_collection_accounting_details,
)


DENOMINATIONS = (10, 20, 50, 100, 500, 1000, 5000)


class BoxCollection(Document):
	def before_insert(self):
		if not self.flags.from_donation_box:
			frappe.throw(
				frappe._(
					"Box Collection records are created automatically when a Donation Box is submitted."
				)
			)

	def validate(self):
		self.set_box_details()
		self.populate_location_from_master()
		self.validate_single_collection_per_box()
		self.validate_status_change_uses_action()
		self.validate_issued_fields_are_locked()
		if not self.status:
			self.status = "Available"

	def set_box_details(self):
		if not self.box_number:
			return

		donation_head, box_shape, box_code = frappe.db.get_value(
			"Donation Box",
			self.box_number,
			["donation_head", "box_shape", "box_code"],
		)
		self.donation_head = donation_head
		self.box_shape = box_shape
		self.box_code = box_code

	def validate_single_collection_per_box(self):
		if not self.box_number:
			return

		existing_box_collection = frappe.db.exists(
			"Box Collection",
			{
				"box_number": self.box_number,
				"name": ["!=", self.name],
				"docstatus": ["!=", 2],
			},
		)
		if existing_box_collection:
			frappe.throw(
				frappe._("Donation Box {0} already has Box Collection {1}.").format(
					self.box_number,
					existing_box_collection,
				)
			)

	def validate_status_change_uses_action(self):
		if self.is_new() or self.docstatus != 1:
			return

		previous_status = frappe.db.get_value("Box Collection", self.name, "status")
		if previous_status != self.status and not self.flags.box_collection_action:
			frappe.throw(frappe._("Use the Box Collection action buttons to change status."))

	def validate_issued_fields_are_locked(self):
		if self.is_new() or self.docstatus != 1:
			return

		previous_status = frappe.db.get_value("Box Collection", self.name, "status")
		if previous_status != "Issued" or self.status != "Issued":
			return

		locked_fields = (
			("donation_location", "Donation Location"),
			("location_type", "Location Type"),
			("location_name", "Shop/House Name"),
			("donor_location", "Address for Box Delivery"),
			("contact", "Contact"),
			("contact_number", "Contact Number"),
			("care_of_trustee", "Care Of Trustee"),
			("care_of_donor", "Care Of Donor"),
			("deployment_officer", "Delivery Staff"),
			("assignment_date", "Assignment Date"),
			("box_number", "Donation Box"),
			("box_code", "Box Code"),
			("donation_head", "Donation Head"),
			("box_shape", "Box Shape"),
		)
		changed_fields = [
			label for fieldname, label in locked_fields if self.has_value_changed(fieldname)
		]
		if changed_fields:
			frappe.throw(
				frappe._("Issued Box Collection fields cannot be changed: {0}").format(
					", ".join(changed_fields)
				)
			)

	@frappe.whitelist()
	def set_issuance_date(
		self,
		donation_location=None,
		location_type=None,
		location_name=None,
		donor_location=None,
		contact=None,
		contact_number=None,
		care_of_trustee=None,
		care_of_donor=None,
		deployment_officer=None,
	):
		self.issue_box(
			action_type="Issuance",
			donation_location=donation_location,
			location_type=location_type,
			location_name=location_name,
			donor_location=donor_location,
			contact=contact,
			contact_number=contact_number,
			care_of_trustee=care_of_trustee,
			care_of_donor=care_of_donor,
			deployment_officer=deployment_officer,
		)
		return "Assignment date set"

	@frappe.whitelist()
	def set_reissuance_date(
		self,
		donation_location=None,
		location_type=None,
		location_name=None,
		donor_location=None,
		contact=None,
		contact_number=None,
		care_of_trustee=None,
		care_of_donor=None,
		deployment_officer=None,
	):
		self.issue_box(
			action_type="Reissuance",
			donation_location=donation_location,
			location_type=location_type,
			location_name=location_name,
			donor_location=donor_location,
			contact=contact,
			contact_number=contact_number,
			care_of_trustee=care_of_trustee,
			care_of_donor=care_of_donor,
			deployment_officer=deployment_officer,
		)
		return "Reassignment date set"

	def issue_box(
		self,
		action_type,
		donation_location=None,
		location_type=None,
		location_name=None,
		donor_location=None,
		contact=None,
		contact_number=None,
		care_of_trustee=None,
		care_of_donor=None,
		deployment_officer=None,
	):
		self.ensure_submitted()

		if action_type == "Issuance" and self.status not in ("Available", "Collected"):
			frappe.throw(frappe._("Only Available or Collected boxes can be issued."))

		if action_type == "Reissuance" and self.status != "Collected":
			frappe.throw(frappe._("Only Collected boxes can be reissued."))

		self.donation_location = donation_location or self.donation_location
		self.location_type = location_type or self.location_type
		self.location_name = location_name or self.location_name
		self.donor_location = donor_location or self.donor_location
		self.contact = contact or self.contact
		self.contact_number = contact_number or self.contact_number
		self.care_of_trustee = care_of_trustee or self.care_of_trustee
		self.care_of_donor = care_of_donor or self.care_of_donor
		self.deployment_officer = deployment_officer or self.deployment_officer

		self.populate_location_from_master(force=True)

		self.validate_assignment_details()
		self.status = "Issued"
		self.assignment_date = today()
		self.collection_date = None
		self.collection_office = None
		self.collected_amount = 0
		self.flags.box_collection_action = True
		self.save(ignore_permissions=True)
		self.create_action_log(action_type)

	@frappe.whitelist()
	def set_collection_date(
		self,
		collection_office=None,
		collected_amount=None,
		denominations=None,
		mode_of_payment=None,
		debit_account=None,
		credit_account=None,
	):
		self.ensure_submitted()

		if self.status != "Issued":
			frappe.throw(frappe._("Only Issued boxes can be collected."))

		self.collection_office = collection_office or self.collection_office
		if not self.collection_office:
			frappe.throw(frappe._("Collection Staff is required."))

		denomination_rows = self.get_denomination_rows(denominations)
		denomination_total = sum(row["amount"] for row in denomination_rows)
		collected_amount = flt(collected_amount)

		if collected_amount <= 0:
			frappe.throw(frappe._("Collected Amount must be greater than zero."))

		if denomination_total != collected_amount:
			frappe.throw(
				frappe._("Denomination total {0} must match Collected Amount {1}.").format(
					frappe.format_value(denomination_total, {"fieldtype": "Currency"}),
					frappe.format_value(collected_amount, {"fieldtype": "Currency"}),
				)
			)

		self.mode_of_payment = mode_of_payment or self.mode_of_payment
		self.debit_account = debit_account or self.debit_account
		self.credit_account = credit_account or self.credit_account
		set_collection_accounting_details(self, "Box Collection", self.donation_head)
		validate_collection_accounting_details(
			self,
			"Box Collection",
			self.donation_head,
			collected_amount,
		)

		self.status = "Collected"
		self.collection_date = today()
		self.collected_amount = collected_amount
		self.flags.box_collection_action = True
		self.save(ignore_permissions=True)
		log_name = self.create_action_log("Collection", denomination_rows=denomination_rows)
		journal_entry = create_collection_journal_entry(
			self,
			source_type="Box Collection",
			donation_type=self.donation_head,
			amount=self.collected_amount,
			posting_date=self.collection_date,
			remarks=self.get_collection_accounting_remarks(),
			received_from=self.get_collection_received_from(),
			reference_name=log_name,
		)
		frappe.db.set_value("Box Collection Log", log_name, "journal_entry", journal_entry, update_modified=False)
		return "Collection date set"

	def ensure_submitted(self):
		if self.docstatus != 1:
			frappe.throw(frappe._("Submit the Box Collection before performing actions."))

	def validate_assignment_details(self):
		missing_fields = []
		if not self.donation_location:
			missing_fields.append("Donation Location")
		if not self.deployment_officer:
			missing_fields.append("Delivery Staff")

		if missing_fields:
			frappe.throw(frappe._("Missing assignment details: {0}").format(", ".join(missing_fields)))

	def populate_location_from_master(self, force=False):
		if not self.donation_location:
			return

		if not force and not (self.is_new() or self.has_value_changed("donation_location")):
			return

		location = frappe.db.get_value(
			"Donation Location",
			self.donation_location,
			["location_type", "contact", "contact_person", "shophouse_name", "address"],
			as_dict=True,
		)
		if not location:
			return

		self.location_type = location.location_type
		self.contact_number = location.contact
		self.contact = location.contact_person
		self.location_name = location.shophouse_name
		self.donor_location = location.address

	def get_denomination_rows(self, denominations):
		denominations = frappe.parse_json(denominations) if isinstance(denominations, str) else denominations
		denominations = denominations or []
		denomination_counts = {}

		if isinstance(denominations, dict):
			denomination_counts = {cint(denomination): cint(count) for denomination, count in denominations.items()}
		else:
			for row in denominations:
				denomination_counts[cint(row.get("denomination"))] = cint(row.get("note_count") or row.get("count"))

		rows = []
		for denomination in DENOMINATIONS:
			note_count = denomination_counts.get(denomination, 0)
			if note_count < 0:
				frappe.throw(frappe._("Note count cannot be negative for denomination {0}.").format(denomination))

			rows.append(
				{
					"denomination": str(denomination),
					"note_count": note_count,
					"amount": denomination * note_count,
				}
			)

		if not any(row["note_count"] for row in rows):
			frappe.throw(frappe._("At least one denomination count is required."))

		invalid_denominations = set(denomination_counts) - set(DENOMINATIONS)
		if invalid_denominations:
			frappe.throw(
				frappe._("Invalid denominations: {0}").format(
					", ".join(str(denomination) for denomination in sorted(invalid_denominations))
				)
			)

		return rows

	def create_action_log(self, action_type, denomination_rows=None):
		staff = self.collection_office if action_type == "Collection" else self.deployment_officer
		log = frappe.get_doc(
			{
				"doctype": "Box Collection Log",
				"box_collection": self.name,
				"action": action_type,
				"action_date": now_datetime(),
				"status_after": self.status,
				"donation_box": self.box_number,
				"box_number": frappe.db.get_value("Donation Box", self.box_number, "box_number"),
				"box_code": self.box_code,
				"donation_head": self.donation_head,
				"box_shape": self.box_shape,
				"location_type": self.location_type,
				"location_name": self.location_name,
				"donor_location": self.donor_location,
				"contact": self.contact,
				"staff": staff,
				"collected_amount": self.collected_amount if action_type == "Collection" else 0,
				"cash_denominations": denomination_rows or [],
			}
		).insert(ignore_permissions=True)
		return log.name

	def get_collection_accounting_remarks(self):
		return "Box Collection: {0} | Box Code: {1} | Donation Head: {2} | Location: {3}".format(
			self.name,
			self.box_code,
			self.donation_head,
			self.location_name,
		)

	def get_collection_received_from(self):
		return "Box Collection {0} ({1})".format(self.name, self.box_code or self.box_number)
