import json

import frappe


def execute():
	_remove_donor_cnic_from_list_view_settings()
	_remove_donor_cnic_from_user_settings()


def _remove_donor_cnic_from_list_view_settings():
	if not frappe.db.table_exists("List View Settings"):
		return

	for row in frappe.get_all("List View Settings", filters={"name": "Donation Order"}, pluck="name"):
		fields = frappe.db.get_value("List View Settings", row, "fields")
		if not fields:
			continue

		updated_fields = _replace_donor_cnic_field(json.loads(fields))
		if updated_fields is not None:
			frappe.db.set_value("List View Settings", row, "fields", json.dumps(updated_fields))


def _remove_donor_cnic_from_user_settings():
	if not frappe.db.table_exists("__UserSettings"):
		return

	for row in frappe.db.sql(
		"""
		select user, doctype, data
		from `__UserSettings`
		where doctype = %s
		""",
		("Donation Order",),
		as_dict=True,
	):
		try:
			settings = json.loads(row.data or "{}")
		except json.JSONDecodeError:
			continue

		list_settings = settings.get("List", {})
		updated_fields = _replace_donor_cnic_field(list_settings.get("fields"))
		if updated_fields is None:
			continue

		list_settings["fields"] = updated_fields
		settings["List"] = list_settings
		frappe.db.sql(
			"""
			update `__UserSettings`
			set data = %s
			where user = %s and doctype = %s
			""",
			(json.dumps(settings), row.user, row.doctype),
		)


def _replace_donor_cnic_field(fields):
	if not isinstance(fields, list):
		return None

	updated = False
	new_fields = []
	for field in fields:
		fieldname = field.get("fieldname") if isinstance(field, dict) else field
		if fieldname == "donor_cnic":
			updated = True
			if not any(
				(f.get("fieldname") if isinstance(f, dict) else f) == "donor_email" for f in fields
			):
				new_fields.append({"fieldname": "donor_email", "label": "Donor Email"})
			continue
		new_fields.append(field)

	return new_fields if updated else None
