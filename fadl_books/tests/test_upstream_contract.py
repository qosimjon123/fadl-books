from pathlib import Path

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate
from frappe_books.reports import dashboard as native
from frappe_books.tests.accounting import make_account

FRIDAY = "2026-11-20 12:00:00"
ENDPOINTS = ("get_cashflow", "get_profit_and_loss", "get_top_expenses", "get_invoice_summary")

# What the overrides import from the native module; a rename must fail here, not in production.
NATIVE_HELPERS = (
	"_monthly_totals", "_months", "_balance", "_ledger_filters", "_invoice_totals",
	"LEDGER", "INVOICE_DOCTYPES", "MONTH_FIELDS", "CASH_ACCOUNTS",
	"DEBIT_MINUS_CREDIT", "CREDIT_MINUS_DEBIT", "get_period_dates",
)

# Fields our queries and db_inserts rely on; a renamed field must fail here.
FIELD_CONTRACT = {
	"Books GL Entry": ("posting_date", "account", "debit", "credit", "is_cancelled"),
	"Books Account": ("root_type", "account_type"),
	"Books Sales Invoice": ("posting_date", "base_grand_total", "outstanding_amount"),
	"Books Purchase Invoice": ("posting_date", "base_grand_total", "outstanding_amount"),
	"Books Payment Entry": ("posting_date", "payment_type", "paid_amount", "received_amount", "unallocated_amount"),
	"Books Stock Ledger Entry": ("posting_date", "item_code", "actual_qty", "stock_value_difference", "is_cancelled"),
}

# Fork edits inside native frontend files; a merge that drops them fails here.
FRONTEND_MARKERS = {
	"src/pages/Dashboard/Dashboard.vue": (
		"import PeriodSelector from './FadlPeriodSelector.vue'",
		"FadlCustomCards",
		"period: 'Today'",
	),
	"src/mobile/MobileTabs.vue": ("from './fadlTabs'",),
	"src/router.ts": ("FadlMore/FadlMorePage.vue",),
}
FRONTEND_FILES = (
	"src/pages/Dashboard/FadlPeriodSelector.vue",
	"src/pages/Dashboard/FadlCustomCards.vue",
	"src/mobile/fadlTabs.ts",
	"src/pages/FadlMore/FadlMorePage.vue",
)


class IntegrationTestUpstreamContract(IntegrationTestCase):
	def test_native_endpoints_exist_and_are_whitelisted(self):
		for name in ENDPOINTS:
			fn = frappe.get_attr(f"frappe_books.reports.dashboard.{name}")
			self.assertIn(fn, frappe.whitelisted)

	def test_overrides_are_registered_and_whitelisted(self):
		for name in ENDPOINTS:
			path = frappe.override_whitelisted_method(f"frappe_books.reports.dashboard.{name}")
			self.assertEqual(path, f"fadl_books.dashboard_overrides.{name}")
			self.assertIn(frappe.get_attr(path), frappe.whitelisted)

	def test_native_helpers_and_constants_exist(self):
		for name in NATIVE_HELPERS:
			self.assertTrue(hasattr(native, name), f"frappe_books.reports.dashboard.{name} is gone")

	def test_native_period_keys_still_resolve(self):
		with self.freeze_time(FRIDAY):
			for key in ("This Year", "This Quarter", "This Month", "YTD"):
				from_date, to_date = native.get_period_dates(key)
				self.assertEqual(to_date, getdate("2026-11-20"))
				self.assertLessEqual(from_date, to_date)

	def test_fields_our_queries_use_exist(self):
		for doctype, fieldnames in FIELD_CONTRACT.items():
			meta = frappe.get_meta(doctype)
			for fieldname in fieldnames:
				self.assertIsNotNone(meta.get_field(fieldname), f"{doctype}.{fieldname} is gone")

	def test_native_keys_delegate_byte_for_byte(self):
		"""With data in the period, each override must equal the native answer."""
		cash = make_account("Contract Cash", account_type="Cash")
		rent = make_account("Contract Rent", root_type="Expense")
		for date, account, debit, credit in (
			("2026-11-05", cash, 100, 0),
			("2026-11-05", rent, 30, 0),
			("2026-11-10", cash, 0, 20),
		):
			frappe.get_doc({
				"doctype": "Books GL Entry", "posting_date": date,
				"account": account.name, "debit": debit, "credit": credit,
			}).insert()
		frappe.get_doc({
			"doctype": "Books Sales Invoice", "name": frappe.generate_hash(),
			"posting_date": "2026-11-10", "docstatus": 1,
			"base_grand_total": 100, "outstanding_amount": 40,
		}).db_insert()

		with self.freeze_time(FRIDAY):
			for name in ENDPOINTS:
				ours = frappe.get_attr(f"fadl_books.dashboard_overrides.{name}")
				native_fn = getattr(native, name)
				args = {"period": "This Month"}
				if name == "get_invoice_summary":
					args["doctype"] = "Books Sales Invoice"
				self.assertEqual(ours(**args), native_fn(**args), f"{name} diverged from native")

	def test_frontend_fork_markers_survived(self):
		root = Path(frappe.get_app_path("frappe_books")).parent / "frontend"
		for rel, markers in FRONTEND_MARKERS.items():
			text = (root / rel).read_text()
			for marker in markers:
				self.assertIn(marker, text, f"{rel} lost fork edit: {marker}")
		for rel in FRONTEND_FILES:
			self.assertTrue((root / rel).exists(), f"{rel} is missing")