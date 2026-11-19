import frappe
from frappe import _
from frappe.utils import add_days
from frappe_books.accounting.money import as_decimal, rounded
from frappe_books.reports import dashboard as native
from frappe_books.reports.filters import datetime_conditions

from fadl_books.periods import get_period_dates, is_custom_period


@frappe.whitelist()
def get_cashflow(period: str) -> dict:
	if not is_custom_period(period):
		return native.get_cashflow(period)
	from_date, to_date = get_period_dates(period)
	fields = [*native.MONTH_FIELDS, {"SUM": "debit", "as": "inflow"}, {"SUM": "credit", "as": "outflow"}]
	totals = native._monthly_totals(from_date, to_date, native.CASH_ACCOUNTS, fields)
	months = [
		{
			"yearmonth": month,
			"inflow": rounded(totals[month].inflow if month in totals else 0),
			"outflow": rounded(totals[month].outflow if month in totals else 0),
		}
		for month in native._months(from_date, to_date)
	]
	return {"months": months, "has_data": bool(totals)}


@frappe.whitelist()
def get_profit_and_loss(period: str) -> dict:
	if not is_custom_period(period):
		return native.get_profit_and_loss(period)
	from_date, to_date = get_period_dates(period)
	income = native._monthly_totals(
		from_date, to_date, {"account.root_type": "Income"},
		[*native.MONTH_FIELDS, native.CREDIT_MINUS_DEBIT],
	)
	expense = native._monthly_totals(
		from_date, to_date, {"account.root_type": "Expense"},
		[*native.MONTH_FIELDS, native.DEBIT_MINUS_CREDIT],
	)
	months = [
		{"yearmonth": month, "balance": native._balance(income, month) - native._balance(expense, month)}
		for month in native._months(from_date, to_date)
	]
	return {"months": months, "has_data": bool(income or expense)}


@frappe.whitelist()
def get_top_expenses(period: str) -> list[dict]:
	if not is_custom_period(period):
		return native.get_top_expenses(period)
	from_date, to_date = get_period_dates(period)
	rows = frappe.get_list(
		native.LEDGER,
		filters=native._ledger_filters(from_date, to_date, {"account.root_type": "Expense"}),
		fields=["account", native.DEBIT_MINUS_CREDIT],
		group_by="account",
		order_by="account",
	)
	spent = sorted((row for row in rows if row.balance > 0), key=lambda row: row.balance, reverse=True)
	expenses = [{"account": row.account, "total": rounded(row.balance)} for row in spent[:5]]
	if others := spent[5:]:
		expenses.append({"account": _("Others"), "total": rounded(sum(row.balance for row in others))})
	return expenses


@frappe.whitelist()
def get_invoice_summary(doctype: str, period: str) -> dict:
	if not is_custom_period(period):
		return native.get_invoice_summary(doctype, period)
	if doctype not in native.INVOICE_DOCTYPES:
		frappe.throw(_("{0} is not an invoice.").format(doctype))
	from_date, to_date = get_period_dates(period)
	conditions = [
		["docstatus", "=", 1],
		*datetime_conditions("posting_date", from_date, to_date),
	]
	paid = native._invoice_totals(doctype, [*conditions, ["outstanding_amount", "=", 0]], "base_grand_total")
	unpaid = native._invoice_totals(doctype, [*conditions, ["outstanding_amount", "!=", 0]], "outstanding_amount")
	return {
		"paid": rounded(as_decimal(paid.amount)),
		"unpaid": rounded(as_decimal(unpaid.amount)),
		"paid_count": paid.count,
		"unpaid_count": unpaid.count,
		"from_date": from_date,
		"before_date": add_days(to_date, 1),
	}