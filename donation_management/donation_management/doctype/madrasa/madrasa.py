# Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class Madrasa(Document):
	def validate(self):
		self.master_id = self.name
		if not self.title and self.madrasa_name:
			self.title = self.madrasa_name
		if not self.madrasa_name and self.title:
			self.madrasa_name = self.title
