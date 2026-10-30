app_name = "masters_association"
app_title = "Masters Association"
app_publisher = "mujeebcpy"
app_description = "Membership Management app"
app_email = "mujeebrahman@wahni.com"
app_license = "mit"

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["Masters Manager", "Association Member", "Solar Monitor Viewer"]]],
	},
	{
		"dt": "Role Profile",
		"filters": [["name", "in", ["Masters Member Portal"]]],
	},
	{
		"dt": "Workflow",
		"filters": [["name", "in", ["Association Member Approval"]]],
	},
	{
		"dt": "List View Settings",
		"filters": [["name", "in", ["Association Member"]]],
	},
]
# Apps
# ------------------

required_apps = ["india_compliance"]

# Each item in the list will be shown as an app in the apps page
add_to_apps_screen = [
	{
		"name": "masters_association",
		"logo": "/assets/masters_association/images/logo/mark-square.png",
		"title": "Masters",
		"route": "/desk/masters",
		"has_permission": "masters_association.api.has_app_permission",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/masters_association/css/masters_association.css"
# app_include_js = "/assets/masters_association/js/masters_association.js"

# include js, css files in header of web template
# web_include_css = "/assets/masters_association/css/masters_association.css"
# web_include_js = "/assets/masters_association/js/masters_association.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "masters_association/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "masters_association/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
home_page = "masters"

# Public website pages rendered by the Vue app in /frontend (served from www/masters.html)
website_route_rules = [
	{"from_route": f"/{route}", "to_route": "masters"}
	for route in (
		"about",
		"become-members",
		"members",
		"gallery",
		"photo-gallery",
		"video-gallery",
		"events",
		"documents",
		"grievance",
		"contact",
		"member",
		"member/profile",
		"member/account",
		"solar",
		"solar/accounts",
	)
] + [{"from_route": "/solar/station/<path:name>", "to_route": "masters"}]

website_redirects = [
	{"source": "/index", "target": "/"},
	{"source": "/event", "target": "/events"},
	{"source": "/members-registration", "target": "/become-members"},
]

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

role_home_page = {"Association Member": "/member/profile"}

extend_doctype_class = {
	"User": ["masters_association.member_portal.MemberUserMixin"],
	"File": ["masters_association.member_files.MemberPhotoFileMixin"],
}

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "masters_association.utils.jinja_methods",
# 	"filters": "masters_association.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "masters_association.install.before_install"
# after_install = "masters_association.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "masters_association.uninstall.before_uninstall"
# after_uninstall = "masters_association.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "masters_association.utils.before_app_install"
# after_app_install = "masters_association.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "masters_association.utils.before_app_uninstall"
# after_app_uninstall = "masters_association.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "masters_association.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "masters_association.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["masters_association.search.awesomebar_results"]

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

has_permission = {"*": "masters_association.permissions.has_scoped_permission"}
permission_query_conditions = {"*": "masters_association.permissions.get_scoped_query_conditions"}
auth_hooks = ["masters_association.rpc_permissions.check_rpc_scope"]

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"File": {"before_validate": "masters_association.member_files.validate_member_file"},
	"User": {
		"before_validate": "masters_association.member_portal.validate_user_account",
		"before_rename": "masters_association.member_portal.before_user_rename",
		"after_rename": "masters_association.member_portal.after_user_rename",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"masters_association.tasks.all"
# 	],
# 	"daily": [
# 		"masters_association.tasks.daily"
# 	],
# 	"hourly": [
# 		"masters_association.tasks.hourly"
# 	],
# 	"weekly": [
# 		"masters_association.tasks.weekly"
# 	],
# 	"monthly": [
# 		"masters_association.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "masters_association.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "masters_association.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "masters_association.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "masters_association.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["masters_association.utils.before_request"]
# after_request = ["masters_association.utils.after_request"]

# Job Events
# ----------
# before_job = ["masters_association.utils.before_job"]
# after_job = ["masters_association.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"masters_association.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

scheduler_events = {
	"cron": {
		# After sunset (system time zone), so today's solar energy is final.
		"0 19 * * *": ["masters_association.solar_monitor.schedule.daily_refresh"],
	},
}
