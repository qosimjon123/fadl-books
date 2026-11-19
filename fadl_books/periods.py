import frappe
from frappe import _
from frappe.utils import add_days, get_first_day, getdate
from frappe_books.reports import dashboard as native

# A custom range travels inside the period string: Custom:YYYY-MM-DD:YYYY-MM-DD.
CUSTOM_PREFIX = "Custom:"

# Native keys keep the native resolver, including YTD and its fiscal year.
NATIVE_LABELS = {
	"This Year": "This year",
	"This Quarter": "This quarter",
	"This Month": "This month",
	"YTD": "Year to date",
}


def _today(today):
	return today, today


def _yesterday(today):
	day = add_days(today, -1)
	return day, day


def _last_3_days(today):
	return add_days(today, -2), today


def _this_week(today):
	return add_days(today, -today.weekday()), today


def _last_week(today):
	monday = add_days(today, -today.weekday())
	return add_days(monday, -7), add_days(monday, -1)


def _last_month(today):
	end = add_days(get_first_day(today), -1)
	return get_first_day(end), end


def _last_quarter(today):
	this_quarter = today.replace(day=1, month=3 * ((today.month - 1) // 3) + 1)
	end = add_days(this_quarter, -1)
	return end.replace(day=1, month=3 * ((end.month - 1) // 3) + 1), end


def _last_year(today):
	year = today.year - 1
	return today.replace(year=year, month=1, day=1), today.replace(year=year, month=12, day=31)


# key -> (label, resolver). Add a period here; the selector picks it up from the server.
CUSTOM_PERIODS = {
	"Today": ("Today", _today),
	"Yesterday": ("Yesterday", _yesterday),
	"Last 3 Days": ("Last 3 days", _last_3_days),
	"This Week": ("This week", _this_week),
	"Last Week": ("Last week", _last_week),
	"Last Month": ("Last month", _last_month),
	"Last Quarter": ("Last quarter", _last_quarter),
	"Last Year": ("Last year", _last_year),
}

# Shortest to longest; YTD never exceeds This Year; the custom range goes last.
ORDER = [
	"Today", "Yesterday", "Last 3 Days",
	"This Week", "Last Week",
	"This Month", "Last Month",
	"This Quarter", "Last Quarter",
	"YTD", "This Year", "Last Year",
	"Custom",
]


def is_custom_period(period: str) -> bool:
	return period in CUSTOM_PERIODS or period.startswith(CUSTOM_PREFIX)


def _parse_custom_range(period: str) -> tuple:
	parts = period.split(":")
	if len(parts) != 3:
		frappe.throw(_("Invalid custom period: {0}").format(period))
	try:
		from_date, to_date = getdate(parts[1]), getdate(parts[2])
	except (ValueError, TypeError):
		frappe.throw(_("Invalid custom period: {0}").format(period))
	if from_date > to_date:
		frappe.throw(_("The custom period starts after it ends: {0}").format(period))
	return from_date, to_date


def get_period_dates(period: str) -> tuple:
	"""Custom periods resolve here; native keys delegate to the native resolver."""
	if period.startswith(CUSTOM_PREFIX):
		return _parse_custom_range(period)
	if period in CUSTOM_PERIODS:
		return CUSTOM_PERIODS[period][1](getdate())
	return native.get_period_dates(period)


@frappe.whitelist()
def get_period_options() -> list[dict]:
	"""Selector options with translated labels, shortest period first."""
	labels = {
		**NATIVE_LABELS,
		**{key: value[0] for key, value in CUSTOM_PERIODS.items()},
		"Custom": "Custom range",
	}
	return [{"value": key, "label": _(labels[key])} for key in ORDER]