import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	create_custom_fields(get_custom_fields(), update=True)
	update_additional_salary_property_setters()


def get_custom_fields():
	return {
		"Branch": [
			{
				"fieldname": "custom_region",
				"fieldtype": "Link",
				"label": "Region",
				"options": "Region",
				"insert_after": "branch",
			}
		],
		"Cost Center": [
			{
				"fieldname": "custom_budget_hierarchy_section",
				"fieldtype": "Section Break",
				"label": "Budget Hierarchy",
				"insert_after": "parent_cost_center",
			},
			{
				"fieldname": "custom_region",
				"fieldtype": "Link",
				"label": "Region",
				"options": "Region",
				"insert_after": "custom_budget_hierarchy_section",
			},
			{
				"fieldname": "custom_branch",
				"fieldtype": "Link",
				"label": "Branch",
				"options": "Branch",
				"insert_after": "custom_region",
			},
			{
				"fieldname": "custom_madrasa",
				"fieldtype": "Link",
				"label": "Madrasa",
				"options": "Madrasa",
				"insert_after": "custom_branch",
			},
		],
		"Additional Salary": [
			{
				"fieldname": "custom_adjustment_section",
				"fieldtype": "Section Break",
				"label": "Adjustment Controls",
				"insert_after": "amount",
			},
			{
				"fieldname": "custom_adjustment_type",
				"fieldtype": "Select",
				"label": "Adjustment Type",
				"options": "\nRegular\nOvertime\nSalary Excess",
				"insert_after": "custom_adjustment_section",
			},
			{
				"fieldname": "custom_paused",
				"fieldtype": "Check",
				"label": "Paused",
				"insert_after": "custom_adjustment_type",
				"allow_on_submit": 1,
			},
			{
				"fieldname": "custom_overtime_hours",
				"fieldtype": "Float",
				"label": "Overtime Hours",
				"depends_on": "eval:doc.custom_adjustment_type == 'Overtime'",
				"insert_after": "custom_paused",
			},
			{
				"fieldname": "custom_overtime_rate",
				"fieldtype": "Currency",
				"label": "Overtime Rate",
				"options": "currency",
				"depends_on": "eval:doc.custom_adjustment_type == 'Overtime'",
				"insert_after": "custom_overtime_hours",
			},
			{
				"fieldname": "custom_balance_column",
				"fieldtype": "Column Break",
				"insert_after": "custom_overtime_rate",
			},
			{
				"fieldname": "custom_total_adjustment_amount",
				"fieldtype": "Currency",
				"label": "Total Adjustment Amount",
				"options": "currency",
				"insert_after": "custom_balance_column",
			},
			{
				"fieldname": "custom_paid_or_deducted_amount",
				"fieldtype": "Currency",
				"label": "Paid / Deducted Amount",
				"options": "currency",
				"insert_after": "custom_total_adjustment_amount",
				"allow_on_submit": 1,
			},
			{
				"fieldname": "custom_remaining_balance",
				"fieldtype": "Currency",
				"label": "Remaining Balance",
				"options": "currency",
				"read_only": 1,
				"insert_after": "custom_paid_or_deducted_amount",
				"allow_on_submit": 1,
			},
		],
	}


def update_additional_salary_property_setters():
	for fieldname in ("disabled",):
		if frappe.db.exists(
			"Property Setter",
			{
				"doc_type": "Additional Salary",
				"field_name": fieldname,
				"property": "allow_on_submit",
			},
		):
			continue

		frappe.get_doc(
			{
				"doctype": "Property Setter",
				"doctype_or_field": "DocField",
				"doc_type": "Additional Salary",
				"field_name": fieldname,
				"property": "allow_on_submit",
				"property_type": "Check",
				"value": "1",
			}
		).insert(ignore_permissions=True)
