// Copyright (c) 2026, osama.ahmed@deliverydevs.com and contributors
// For license information, please see license.txt

frappe.ui.form.on("Data Import", {
	refresh(frm) {
		if (frm.has_import_file && frm.has_import_file() && !frm.doc.reference_doctype) {
			frm.set_intro(
				__("Select Document Type before previewing or starting the import."),
				"orange"
			);
		} else if (!frm.doc.__donor_import_intro) {
			frm.set_intro("");
		}
	},

	reference_doctype(frm) {
		if (frm.doc.reference_doctype === "Donor") {
			frappe.db.get_doc("Donation Settings", "Donation Settings").then((settings) => {
				const messages = [];

				if (cint(settings.allow_donor_without_phone_or_email)) {
					messages.push(__("Phone or Email is optional."));
				} else {
					messages.push(
						__("Each row needs Donor Phone Number or Donor Email unless allowed in Donation Settings.")
					);
				}

				if (cint(settings.allow_duplicate_donor_phone)) {
					messages.push(__("Duplicate phone numbers are allowed."));
				} else {
					messages.push(__("Duplicate phone numbers are not allowed."));
				}

				frm.set_intro(__("Donor import: {0}", [messages.join(" ")]), "blue");
				frm.doc.__donor_import_intro = 1;
			});
			return;
		}

		frm.doc.__donor_import_intro = 0;
		if (!frm.has_import_file || !frm.has_import_file()) {
			frm.set_intro("");
		}
	},
});
