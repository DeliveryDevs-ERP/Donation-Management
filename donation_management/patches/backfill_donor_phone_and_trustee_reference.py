import frappe

from donation_management.donation_management.doctype.donor.donor import normalize_phone


def execute():
	convert_existing_trustee_donors()
	backfill_donor_phone_digits()


def convert_existing_trustee_donors():
	if not frappe.db.has_column("Donor", "existing_trustee"):
		return

	for donor in frappe.get_all(
		"Donor",
		filters={"customer_type": "Existing Trustee"},
		fields=["name", "existing_trustee"],
	):
		frappe.db.set_value("Donor", donor.name, "customer_type", "Walk-in", update_modified=False)


def backfill_donor_phone_digits():
	seen_phone_digits = {}
	duplicate_phone_digits = {}

	for donor in frappe.get_all("Donor", fields=["name", "donor_phone_number"]):
		phone_digits = normalize_phone(donor.donor_phone_number)
		if not phone_digits:
			frappe.db.set_value("Donor", donor.name, "donor_phone_digits", None, update_modified=False)
			continue

		if phone_digits in seen_phone_digits:
			duplicate_phone_digits.setdefault(phone_digits, [seen_phone_digits[phone_digits]]).append(donor.name)
			continue

		seen_phone_digits[phone_digits] = donor.name
		frappe.db.set_value("Donor", donor.name, "donor_phone_digits", phone_digits, update_modified=False)

	if duplicate_phone_digits:
		messages = [
			f"{phone_digits}: {', '.join(donor_names)}"
			for phone_digits, donor_names in sorted(duplicate_phone_digits.items())
		]
		frappe.throw(
			frappe._("Duplicate Donor Phone Numbers must be cleaned before migration: {0}").format(
				"; ".join(messages)
			)
		)
