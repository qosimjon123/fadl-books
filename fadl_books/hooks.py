app_name = "fadl_books"
app_title = "Fadl Books"
app_publisher = "FadlTech team"
app_description = "Extension for frappe book by fadl tech team"
app_email = "fadltech@gmail.com"
app_license = "unlicense"

# Send non-GET requests for this app's endpoints as native `application/json`
# bodies instead of form-encoded, per-key JSON-stringified values.
use_json_request_body = True

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "fadl_books",
# 		"logo": "/assets/fadl_books/logo.png",
# 		"title": "Fadl Books",
# 		"route": "/fadl_books",
# 		"has_permission": "fadl_books.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `fadl_books/dock/fadl_books/fadl_books.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/fadl_books/css/fadl_books.css"
# app_include_js = "/assets/fadl_books/js/fadl_books.js"

# include js, css files in header of web template
# web_include_css = "/assets/fadl_books/css/fadl_books.css"
# web_include_js = "/assets/fadl_books/js/fadl_books.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "fadl_books/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "fadl_books/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Setup Wizard
# ------------

# open a fresh site's setup in this app's own UI instead of the desk wizard.
# must be a non-desk route (not under /desk or /app); to customize setup within
# desk, use setup_wizard_stages / setup_wizard_complete instead.
# setup_wizard_url = "/fadl_books/setup"

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
# 	"methods": "fadl_books.utils.jinja_methods",
# 	"filters": "fadl_books.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "fadl_books.install.before_install"
# after_install = "fadl_books.install.execute"

# Uninstallation
# ------------

# before_uninstall = "fadl_books.uninstall.before_uninstall"
# after_uninstall = "fadl_books.uninstall.after_uninstall"

# Disable / Enable
# ----------------
# Called when this app is logically disabled or re-enabled on a site,
# without uninstalling it. Use this to hide/restore fields this app adds
# to other apps' doctypes.

# before_disable = "fadl_books.uninstall.before_disable"
# after_disable = "fadl_books.uninstall.after_disable"
# before_enable = "fadl_books.install.before_enable"
# after_enable = "fadl_books.install.after_enable"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "fadl_books.utils.before_app_install"
# after_app_install = "fadl_books.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "fadl_books.utils.before_app_uninstall"
# after_app_uninstall = "fadl_books.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "fadl_books.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "fadl_books.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "fadl_books.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["fadl_books.search.awesomebar_results"]

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

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"fadl_books.tasks.all"
# 	],
# 	"daily": [
# 		"fadl_books.tasks.daily"
# 	],
# 	"hourly": [
# 		"fadl_books.tasks.hourly"
# 	],
# 	"weekly": [
# 		"fadl_books.tasks.weekly"
# 	],
# 	"monthly": [
# 		"fadl_books.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "fadl_books.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "fadl_books.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "fadl_books.event.get_events"
# }
# Overriding Methods
# ------------------------------
override_whitelisted_methods = {
	"frappe_books.reports.dashboard.get_cashflow": "fadl_books.dashboard_overrides.get_cashflow",
	"frappe_books.reports.dashboard.get_profit_and_loss": "fadl_books.dashboard_overrides.get_profit_and_loss",
	"frappe_books.reports.dashboard.get_top_expenses": "fadl_books.dashboard_overrides.get_top_expenses",
	"frappe_books.reports.dashboard.get_invoice_summary": "fadl_books.dashboard_overrides.get_invoice_summary",
	# The Books frontend builds mapper paths as frappe_books.<module>.doctype...;
	# Books Loan lives in fadl_books, so its synthetic path routes to the real mapper.
	"frappe_books.fadl_books.doctype.books_loan.books_loan.make_repayment": "fadl_books.fadl_books.doctype.books_loan.books_loan.make_repayment",
}

# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "fadl_books.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["fadl_books.utils.before_request"]
# after_request = ["fadl_books.utils.after_request"]

# Job Events
# ----------
# before_job = ["fadl_books.utils.before_job"]
# after_job = ["fadl_books.utils.after_job"]

# after_file_upload = ["fadl_books.utils.after_file_upload"]

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
# 	"fadl_books.auth.validate"
# ]

# on_social_login = "fadl_books.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
export_python_type_annotations = True

# Require all whitelisted methods to have type annotations
require_type_annotated_api_methods = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

