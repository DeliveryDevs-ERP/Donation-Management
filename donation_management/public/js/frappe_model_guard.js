(function () {
	if (!frappe.model || !frappe.model.with_doctype) {
		return;
	}

	const load_doctype = frappe.model.with_doctype.bind(frappe.model);

	frappe.model.with_doctype = function (doctype, callback, async) {
		if (!doctype) {
			callback && callback();
			return Promise.resolve();
		}

		return load_doctype(doctype, callback, async);
	};
})();
