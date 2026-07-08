frappe.listview_settings["Donor Program Enrollment"] = {
	onload(listview) {
		hide_add_button(listview);
	},
	refresh(listview) {
		hide_add_button(listview);
	},
};

function hide_add_button(listview) {
	listview.page.clear_primary_action();
}
