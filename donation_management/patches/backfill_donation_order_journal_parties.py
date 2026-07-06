import frappe


def execute():
	ensure_donor_party_type()
	backfill_journal_entry_accounts()
	backfill_gl_entries()


def ensure_donor_party_type():
	if frappe.db.exists("Party Type", "Donor"):
		frappe.db.set_value("Party Type", "Donor", "account_type", "Cash", update_modified=False)
		return

	frappe.get_doc(
		{
			"doctype": "Party Type",
			"party_type": "Donor",
			"account_type": "Cash",
		}
	).insert(ignore_permissions=True)


def backfill_journal_entry_accounts():
	if not frappe.db.table_exists("Donation Order") or not frappe.db.table_exists("Journal Entry Account"):
		return

	frappe.db.sql(
		"""
		update `tabJournal Entry Account` journal_account
		inner join `tabDonation Order` donation_order
			on donation_order.journal_entry = journal_account.parent
		inner join `tabJournal Entry` journal_entry
			on journal_entry.name = journal_account.parent
		set journal_account.party_type = 'Donor',
			journal_account.party = donation_order.donor_name
		where journal_entry.docstatus != 2
			and ifnull(donation_order.donor_name, '') != ''
		"""
	)


def backfill_gl_entries():
	if not frappe.db.table_exists("Donation Order") or not frappe.db.table_exists("GL Entry"):
		return

	frappe.db.sql(
		"""
		update `tabGL Entry` gl_entry
		inner join `tabDonation Order` donation_order
			on donation_order.journal_entry = gl_entry.voucher_no
		set gl_entry.party_type = 'Donor',
			gl_entry.party = donation_order.donor_name
		where gl_entry.voucher_type = 'Journal Entry'
			and ifnull(gl_entry.is_cancelled, 0) = 0
			and ifnull(donation_order.donor_name, '') != ''
		"""
	)
