# Copyright (c) 2026, osama.ahmed@deliverydevs.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBoxCollection(FrappeTestCase):
	def make_donation_box(self, donation_head="Zakat"):
		box = frappe.get_doc(
			{
				"doctype": "Donation Box",
				"box_number": f"TEST-{frappe.generate_hash(length=8)}",
				"donation_head": donation_head,
			}
		)
		box.insert()
		box.submit()
		return box

	def get_box_collection(self, box):
		return frappe.get_doc("Box Collection", {"box_number": box.name})

	def test_shape_derives_from_donation_head(self):
		box = self.make_donation_box("Zakat")
		self.assertEqual(box.box_shape, "Square")

	def test_submit_donation_box_creates_submitted_collection(self):
		box = self.make_donation_box("Atiya")
		box_collection = self.get_box_collection(box)

		self.assertEqual(box_collection.docstatus, 1)
		self.assertEqual(box_collection.status, "Available")
		self.assertEqual(box_collection.donation_head, "Atiya")
		self.assertEqual(box_collection.box_shape, "Triangle")

	def test_duplicate_box_collection_is_blocked(self):
		box = self.make_donation_box("Sadqa")

		duplicate = frappe.get_doc(
			{
				"doctype": "Box Collection",
				"box_number": box.name,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			duplicate.insert()

	def test_collection_before_issuance_is_blocked(self):
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)

		with self.assertRaises(frappe.ValidationError):
			box_collection.set_collection_date(
				collection_office="Collector",
				collected_amount=100,
				denominations={100: 1},
			)

	def test_issuance_while_issued_is_blocked(self):
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)
		box_collection.set_issuance_date(
			location_type="Office",
			location_name="Test Shop",
			donor_location="Test Address",
			deployment_officer="Dispatcher",
		)
		box_collection.reload()

		with self.assertRaises(frappe.ValidationError):
			box_collection.set_issuance_date(
				location_type="Office",
				location_name="Another Shop",
				donor_location="Another Address",
				deployment_officer="Dispatcher",
			)

	def test_denomination_total_mismatch_is_blocked(self):
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)
		box_collection.set_issuance_date(
			location_type="Office",
			location_name="Test Shop",
			donor_location="Test Address",
			deployment_officer="Dispatcher",
		)
		box_collection.reload()

		with self.assertRaises(frappe.ValidationError):
			box_collection.set_collection_date(
				collection_office="Collector",
				collected_amount=150,
				denominations={100: 1},
			)

	def test_successful_collection_logs_amount_and_denominations(self):
		box = self.make_donation_box()
		box_collection = self.get_box_collection(box)
		box_collection.set_issuance_date(
			location_type="Office",
			location_name="Test Shop",
			donor_location="Test Address",
			deployment_officer="Dispatcher",
		)
		box_collection.reload()
		box_collection.set_collection_date(
			collection_office="Collector",
			collected_amount=150,
			denominations={100: 1, 50: 1},
		)
		box_collection.reload()

		self.assertEqual(box_collection.status, "Collected")
		self.assertEqual(box_collection.collected_amount, 150)

		collection_log_name = frappe.db.get_value(
			"Box Collection Log",
			{
				"box_collection": box_collection.name,
				"action": "Collection",
			},
			"name",
			order_by="creation desc",
		)
		collection_log = frappe.get_doc("Box Collection Log", collection_log_name)
		self.assertEqual(collection_log.collected_amount, 150)
		self.assertEqual(sum(row.amount for row in collection_log.cash_denominations), 150)
