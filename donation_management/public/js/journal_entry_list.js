const existing_journal_entry_list_settings = frappe.listview_settings["Journal Entry"] || {};
const existing_journal_entry_onload = existing_journal_entry_list_settings.onload;
const existing_journal_entry_refresh = existing_journal_entry_list_settings.refresh;

frappe.listview_settings["Journal Entry"] = {
	...existing_journal_entry_list_settings,

	onload(listview) {
		if (existing_journal_entry_onload) {
			existing_journal_entry_onload(listview);
		}
		hide_cancelled_journal_entries(listview);
	},

	refresh(listview) {
		if (existing_journal_entry_refresh) {
			existing_journal_entry_refresh(listview);
		}
		hide_cancelled_journal_entries(listview);
	},
};

function hide_cancelled_journal_entries(listview) {
	const cancelled_filter = ["Journal Entry", "docstatus", "!=", 2];
	if (
		listview.__hide_cancelled_journal_entries_applied ||
		listview.filter_area.get().some(is_cancelled_journal_entry_filter)
	) {
		listview.__hide_cancelled_journal_entries_applied = true;
		return;
	}

	listview.filter_area.add([cancelled_filter]);
	listview.__hide_cancelled_journal_entries_applied = true;
}

function is_cancelled_journal_entry_filter(filter) {
	return (
		Array.isArray(filter) &&
		filter[0] === "Journal Entry" &&
		filter[1] === "docstatus" &&
		filter[2] === "!=" &&
		Number(filter[3]) === 2
	);
}
