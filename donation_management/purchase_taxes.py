from frappe.utils import flt


PURCHASE_TAX_DOCTYPES = {
	"Purchase Invoice",
	"Purchase Order",
	"Purchase Receipt",
	"Supplier Quotation",
}


def force_purchase_tax_deduction(doc, method=None):
	if doc.doctype not in PURCHASE_TAX_DOCTYPES:
		return

	for row in doc.get("taxes") or []:
		if row.doctype == "Purchase Taxes and Charges" and flt(row.rate):
			row.add_deduct_tax = "Deduct"
