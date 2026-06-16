import frappe
from frappe.utils import add_days, escape_html, getdate, today


def send_pdc_reminders():
	if not frappe.db.table_exists("Donation Order"):
		return

	recipients = get_cfo_recipients()
	if not recipients:
		return

	deposit_cutoff = add_days(today(), 5)
	orders = frappe.get_all(
		"Donation Order",
		filters={
			"mode_of_payment": "Cheque",
			"is_post_dated_cheque": 1,
			"pdc_status": "Pending Deposit",
			"journal_entry": ["is", "not set"],
			"cheque_deposit_date": ["<=", deposit_cutoff],
		},
		fields=[
			"name",
			"donor_name",
			"name_on_donation_slip",
			"donation_amount",
			"currency",
			"cheque_deposit_date",
		],
		order_by="cheque_deposit_date asc",
	)
	if not orders:
		return

	subject = frappe._("PDC Cheques Due for Deposit")
	message = build_pdc_reminder_message(orders)
	frappe.sendmail(
		recipients=recipients,
		subject=subject,
		message=message,
		reference_doctype="Donation Order",
		now=False,
	)


def get_cfo_recipients():
	users = frappe.get_all(
		"Has Role",
		filters={"role": "CFO", "parenttype": "User"},
		pluck="parent",
	)
	if not users:
		return []

	return frappe.get_all(
		"User",
		filters={
			"name": ["in", users],
			"enabled": 1,
			"user_type": "System User",
		},
		pluck="email",
	)


def build_pdc_reminder_message(orders):
	rows = []
	for order in orders:
		rows.append(
			"""
			<tr>
				<td>{name}</td>
				<td>{donor}</td>
				<td>{date}</td>
				<td style="text-align: right;">{amount}</td>
			</tr>
			""".format(
				name=escape_html(order.name),
				donor=escape_html(order.name_on_donation_slip or order.donor_name or ""),
				date=escape_html(str(getdate(order.cheque_deposit_date))),
				amount=frappe.format_value(
					order.donation_amount,
					{"fieldtype": "Currency", "options": order.currency},
				),
			)
		)

	return """
		<p>{intro}</p>
		<table class="table table-bordered" cellpadding="6" cellspacing="0">
			<thead>
				<tr>
					<th>{order_label}</th>
					<th>{donor_label}</th>
					<th>{date_label}</th>
					<th style="text-align: right;">{amount_label}</th>
				</tr>
			</thead>
			<tbody>{rows}</tbody>
		</table>
	""".format(
		intro=frappe._("The following post-dated cheque Donation Orders are due for deposit within 5 days or are overdue."),
		order_label=frappe._("Donation Order"),
		donor_label=frappe._("Donor"),
		date_label=frappe._("Deposit Date"),
		amount_label=frappe._("Amount"),
		rows="\n".join(rows),
	)
