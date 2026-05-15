import frappe


def execute():
	backfill_donation_boxes()
	backfill_box_collections()
	backfill_box_collection_logs()


def backfill_donation_boxes():
	for box in frappe.get_all("Donation Box", fields=["name", "donation_head", "box_number", "box_code"]):
		box_code = get_box_code(box.donation_head, box.box_number)
		if box_code and box.box_code != box_code:
			frappe.db.set_value("Donation Box", box.name, "box_code", box_code, update_modified=False)


def backfill_box_collections():
	for collection in frappe.get_all("Box Collection", fields=["name", "box_number", "box_code"]):
		if not collection.box_number:
			continue

		box_code = frappe.db.get_value("Donation Box", collection.box_number, "box_code")
		if box_code and collection.box_code != box_code:
			frappe.db.set_value("Box Collection", collection.name, "box_code", box_code, update_modified=False)


def backfill_box_collection_logs():
	for log in frappe.get_all("Box Collection Log", fields=["name", "donation_box", "box_code"]):
		if not log.donation_box:
			continue

		box_code = frappe.db.get_value("Donation Box", log.donation_box, "box_code")
		if box_code and log.box_code != box_code:
			frappe.db.set_value("Box Collection Log", log.name, "box_code", box_code, update_modified=False)


def get_box_code(donation_head, box_number):
	if not donation_head or not box_number:
		return None

	return f"{donation_head}-{box_number}"
