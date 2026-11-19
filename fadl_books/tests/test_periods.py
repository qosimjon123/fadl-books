import frappe
from fadl_books.dashboard_overrides import get_cashflow
from fadl_books.periods import (
	CUSTOM_PERIODS,
	ORDER,
	get_period_dates,
	get_period_options,
)
from frappe.tests import IntegrationTestCase
from frappe.utils import getdate

FRIDAY = "2026-11-20 12:00:00"  # a Friday


class IntegrationTestCustomPeriods(IntegrationTestCase):
	def test_custom_period_boundaries(self):
		with self.freeze_time(FRIDAY):
			dates = {key: get_period_dates(key) for key in CUSTOM_PERIODS}

		self.assertEqual(
			dates,
			{
				"Today": (getdate("2026-11-20"), getdate("2026-11-20")),
				"Yesterday": (getdate("2026-11-19"), getdate("2026-11-19")),
				"Last 3 Days": (getdate("2026-11-18"), getdate("2026-11-20")),
				"This Week": (getdate("2026-11-16"), getdate("2026-11-20")),
				"Last Week": (getdate("2026-11-09"), getdate("2026-11-15")),
				"Last Month": (getdate("2026-10-01"), getdate("2026-10-31")),
				"Last Quarter": (getdate("2026-07-01"), getdate("2026-09-30")),
				"Last Year": (getdate("2025-01-01"), getdate("2025-12-31")),
			},
		)

	def test_native_periods_stay_native(self):
		with self.freeze_time(FRIDAY):
			self.assertEqual(
				get_period_dates("This Month"),
				(getdate("2026-11-01"), getdate("2026-11-20")),
			)

	def test_custom_range_is_parsed_from_the_period_string(self):
		self.assertEqual(
			get_period_dates("Custom:2026-01-15:2026-03-02"),
			(getdate("2026-01-15"), getdate("2026-03-02")),
		)

	def test_bad_custom_ranges_are_rejected(self):
		for period in ("Custom:2026-03-02:2026-01-15", "Custom:not-a-date:2026-01-15", "Custom:2026-01-15"):
			with self.assertRaises(frappe.ValidationError):
				get_period_dates(period)

	def test_overrides_are_registered(self):
		for method in ("get_cashflow", "get_profit_and_loss", "get_top_expenses", "get_invoice_summary"):
			self.assertEqual(
				frappe.override_whitelisted_method(f"frappe_books.reports.dashboard.{method}"),
				f"fadl_books.dashboard_overrides.{method}",
			)

	def test_options_are_ordered_shortest_first_and_complete(self):
		values = [option["value"] for option in get_period_options()]
		self.assertEqual(values, ORDER)
		for key in [*CUSTOM_PERIODS, "This Year", "This Quarter", "This Month", "YTD", "Custom"]:
			self.assertIn(key, values)

	def test_chart_endpoint_accepts_a_custom_period(self):
		with self.freeze_time(FRIDAY):
			self.assertEqual(
				[month["yearmonth"] for month in get_cashflow("Last Month")["months"]],
				["2026-10"],
			)
			self.assertEqual(
				[month["yearmonth"] for month in get_cashflow("Today")["months"]],
				["2026-11"],
			)
			self.assertEqual(
				[month["yearmonth"] for month in get_cashflow("Custom:2026-09-10:2026-11-02")["months"]],
				["2026-09", "2026-10", "2026-11"],
			)