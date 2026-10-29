import frappe

no_cache = 1


def get_context(context):
	# Read by the frappe-ui jinjaBootData plugin, which copies each key onto `window`.
	context.boot = {
		"csrf_token": frappe.sessions.get_csrf_token(),
		"site_name": frappe.local.site,
	}
	context.no_breadcrumbs = True
	return context
