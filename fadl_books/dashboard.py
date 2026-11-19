import frappe
from frappe.query_builder import DocType
from frappe.query_builder.functions import Count, Sum

from fadl_books.periods import get_period_dates

GL = DocType("Books GL Entry")
ACCOUNT = DocType("Books Account")
SLE = DocType("Books Stock Ledger Entry")
PE = DocType("Books Payment Entry")


@frappe.whitelist()
def get_dashboard_cards(period: str = "Today") -> list[dict]:
	"""Enabled dashboard cards with their metrics, in row order."""
	settings = frappe.get_single("Books Dashboard Settings")
	from_date, to_date = get_period_dates(period)
	cards = []
	for row in settings.cards:  # already ordered by idx
		if not row.enabled:
			continue
		card = {"name": row.name, "title": row.title, "route": row.route,
		        "color": row.color, "metric_method": row.metric_method,
		        "from_date": from_date, "to_date": to_date,
		        "value": None, "count": 0, "format": "currency"}
		method = row.metric_method
		# только whitelisted-функции из вашего приложения
		if method and method.startswith("fadl_books."):
			try:
				fn = frappe.get_attr(method)
			except AttributeError:
				fn = None  # функция ещё не написана — карточка без цифры
			if fn and fn in frappe.whitelisted:
				metric = fn(period=period)
				card.update(
					value=metric.get("value"),
					count=metric.get("count", 0),
					format=metric.get("format", "currency"),
				)
		cards.append(card)
	return cards


def _totals(query) -> dict:
	row = query.run(as_dict=True)[0]
	return {"value": float(row.value or 0), "count": int(row.count or 0)}


def _invoice_flow(doctype: str, period: str) -> dict:
	inv = DocType(doctype)
	from_date, to_date = get_period_dates(period)
	return _totals(
		frappe.qb.from_(inv)
		.select(Sum(inv.base_grand_total).as_("value"), Count(inv.name).as_("count"))
		.where(inv.docstatus == 1)
		.where(inv.posting_date.between(from_date, to_date))
	)


def _outstanding(doctype: str) -> dict:
	inv = DocType(doctype)
	return _totals(
		frappe.qb.from_(inv)
		.select(Sum(inv.outstanding_amount).as_("value"), Count(inv.name).as_("count"))
		.where(inv.docstatus == 1)
		.where(inv.outstanding_amount != 0)
	)


def _gl_balance(from_date, to_date, credit_first=False, **account_filter) -> float:
	expr = Sum(GL.credit) - Sum(GL.debit) if credit_first else Sum(GL.debit) - Sum(GL.credit)
	q = (
		frappe.qb.from_(GL)
		.join(ACCOUNT).on(GL.account == ACCOUNT.name)
		.select(expr)
		.where(GL.is_cancelled == 0)
		.where(GL.posting_date.between(from_date, to_date))
	)
	for field, value in account_filter.items():
		q = q.where(ACCOUNT[field] == value)
	return float(q.run()[0][0] or 0)


def _payment_flow(payment_type: str, amount_field: str, period: str) -> dict:
	from_date, to_date = get_period_dates(period)
	return _totals(
		frappe.qb.from_(PE)
		.select(Sum(PE[amount_field]).as_("value"), Count(PE.name).as_("count"))
		.where(PE.docstatus == 1)
		.where(PE.payment_type == payment_type)
		.where(PE.posting_date.between(from_date, to_date))
	)


# --- Потоки за период ---

@frappe.whitelist()
def get_sales(period: str) -> dict:
	return _invoice_flow("Books Sales Invoice", period)


@frappe.whitelist()
def get_purchases(period: str) -> dict:
	return _invoice_flow("Books Purchase Invoice", period)


@frappe.whitelist()
def get_gross_profit(period: str) -> dict:
	"""Выручка минус себестоимость за период."""
	from_date, to_date = get_period_dates(period)
	income = _gl_balance(from_date, to_date, credit_first=True, root_type="Income")
	cogs = _gl_balance(from_date, to_date, account_type="Cost of Goods Sold")
	value = income - cogs
	return {"value": value, "percent": round(value / income * 100) if income else 0}


@frappe.whitelist()
def get_receipts(period: str) -> dict:
	return _payment_flow("Receive", "received_amount", period)


@frappe.whitelist()
def get_payments(period: str) -> dict:
	return _payment_flow("Pay", "paid_amount", period)


@frappe.whitelist()
def get_transfers(period: str) -> dict:
	return _payment_flow("Internal Transfer", "paid_amount", period)


@frappe.whitelist()
def get_expenses(period: str) -> dict:
	from_date, to_date = get_period_dates(period)
	return {"value": _gl_balance(from_date, to_date, root_type="Expense")}


@frappe.whitelist()
def get_stock_movements(period: str) -> dict:
	from_date, to_date = get_period_dates(period)
	count = (
		frappe.qb.from_(SLE)
		.select(Count(SLE.name))
		.where(SLE.is_cancelled == 0)
		.where(SLE.posting_date.between(from_date, to_date))
	).run()[0][0]
	return {"value": int(count or 0), "count": int(count or 0), "format": "int"}


# --- Остатки на сейчас: период НЕ применяется ---

@frappe.whitelist()
def get_receivables(period: str | None = None) -> dict:
	"""Нам должны: весь непогашенный долг покупателей, независимо от даты счёта."""
	return _outstanding("Books Sales Invoice")


@frappe.whitelist()
def get_payables(period: str | None = None) -> dict:
	"""Мы должны: весь непогашенный долг поставщикам."""
	return _outstanding("Books Purchase Invoice")


@frappe.whitelist()
def get_stock_balance(period: str | None = None) -> dict:
	"""Остатки: стоимость всего склада и число SKU с ненулевым остатком."""
	value = (
		frappe.qb.from_(SLE)
		.select(Sum(SLE.stock_value_difference))
		.where(SLE.is_cancelled == 0)
	).run()[0][0]
	skus = (
		frappe.qb.from_(SLE)
		.select(SLE.item_code)
		.where(SLE.is_cancelled == 0)
		.groupby(SLE.item_code)
		.having(Sum(SLE.actual_qty) != 0)
	).run()
	return {"value": float(value or 0), "count": len(skus)}


@frappe.whitelist()
def get_advances(period: str | None = None) -> dict:
	"""Займы и авансы: нераспределённые суммы платежей (авансы без привязки к счетам)."""
	return _totals(
		frappe.qb.from_(PE)
		.select(Sum(PE.unallocated_amount).as_("value"), Count(PE.name).as_("count"))
		.where(PE.docstatus == 1)
		.where(PE.unallocated_amount != 0)
	)
