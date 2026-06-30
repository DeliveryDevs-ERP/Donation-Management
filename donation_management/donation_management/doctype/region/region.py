# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class Region(Document):
	def validate(self):
		self.master_id = self.name
		if not self.title and self.region_name:
			self.title = self.region_name
		if not self.region_name and self.title:
			self.region_name = self.title
