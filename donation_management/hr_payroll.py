from frappe.utils import flt


def sync_additional_salary_controls(doc, method=None):
	if doc.get("custom_adjustment_type") == "Overtime":
		hours = flt(doc.get("custom_overtime_hours"))
		rate = flt(doc.get("custom_overtime_rate"))
		if hours and rate:
			doc.amount = hours * rate

	if doc.get("custom_paused"):
		doc.disabled = 1
	elif doc.get("custom_paused") == 0:
		doc.disabled = 0

	total_amount = flt(doc.get("custom_total_adjustment_amount")) or flt(doc.amount)
	doc.custom_total_adjustment_amount = total_amount
	doc.custom_remaining_balance = max(total_amount - flt(doc.get("custom_paid_or_deducted_amount")), 0)
