from frappe.utils import flt


def force_purchase_tax_deduction(doc, method=None):
	for row in doc.get("taxes") or []:
		if row.doctype == "Purchase Taxes and Charges" and flt(row.rate):
			row.add_deduct_tax = "Deduct"
