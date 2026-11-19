import frappe
from fadl_books import dashboard as cards
from frappe.tests import IntegrationTestCase
from frappe_books.tests.accounting import make_account

FRIDAY = "2026-11-20 12:00:00"
TODAY, YESTERDAY, LAST_MONTH = "2026-11-20", "2026-11-19", "2026-10-10"

METRICS = (
	"get_sales", "get_purchases", "get_gross_profit", "get_receipts", "get_payments",
	"get_transfers", "get_expenses", "get_stock_movements",
	"get_receivables", "get_payables", "get_stock_balance", "get_advances",
)


def _gl(account, debit, credit, date):
	frappe.get_doc({
		"doctype": "Books GL Entry", "posting_date": date,
		"account": account.name, "debit": debit, "credit": credit,
	}).insert()


def _invoice(doctype, date, total, outstanding):
	frappe.get_doc({
		"doctype": doctype, "name": frappe.generate_hash(), "posting_date": date,
		"docstatus": 1, "base_grand_total": total, "outstanding_amount": outstanding,
	}).db_insert()


def _payment(payment_type, date, paid=0, received=0, unallocated=0):
	frappe.get_doc({
		"doctype": "Books Payment Entry", "name": frappe.generate_hash(),
		"posting_date": date, "docstatus": 1, "payment_type": payment_type,
		"paid_amount": paid, "received_amount": received, "unallocated_amount": unallocated,
	}).db_insert()


def _sle(date, qty, value, item="Test SKU", cancelled=0):
	frappe.get_doc({
		"doctype": "Books Stock Ledger Entry", "name": frappe.generate_hash(),
		"posting_date": date, "item_code": item, "actual_qty": qty,
		"stock_value_difference": value, "is_cancelled": cancelled,
	}).db_insert()


class IntegrationTestCardMetrics(IntegrationTestCase):
	def setUp(self):
		self.income = make_account("Cards Sales", root_type="Income")
		self.expense = make_account("Cards Rent", root_type="Expense")
		self.cogs = make_account("Cards COGS", root_type="Expense", account_type="Cost of Goods Sold")

		_invoice("Books Sales Invoice", TODAY, 100, 0)
		_invoice("Books Sales Invoice", YESTERDAY, 200, 50)
		_invoice("Books Sales Invoice", LAST_MONTH, 300, 300)
		_invoice("Books Purchase Invoice", TODAY, 80, 80)
		_payment("Receive", TODAY, received=70)
		_payment("Pay", TODAY, paid=40)
		_payment("Internal Transfer", TODAY, paid=10)
		_payment("Receive", LAST_MONTH, received=5, unallocated=25)
		_gl(self.income, 0, 100, TODAY)
		_gl(self.cogs, 40, 0, TODAY)
		_gl(self.expense, 60, 0, TODAY)
		_sle(TODAY, 5, 500)
		_sle(LAST_MONTH, 2, 200)
		_sle(TODAY, 99, 9999, cancelled=1)  # cancelled entries never count

	def test_flow_metrics_follow_the_period(self):
		with self.freeze_time(FRIDAY):
			self.assertEqual(cards.get_sales("Today"), {"value": 100.0, "count": 1})
			self.assertEqual(cards.get_sales("Yesterday"), {"value": 200.0, "count": 1})
			self.assertEqual(cards.get_sales("Last Month"), {"value": 300.0, "count": 1})
			self.assertEqual(
				cards.get_sales(f"Custom:{YESTERDAY}:{TODAY}"), {"value": 300.0, "count": 2}
			)
			self.assertEqual(cards.get_purchases("Today"), {"value": 80.0, "count": 1})
			self.assertEqual(cards.get_receipts("Today"), {"value": 70.0, "count": 1})
			self.assertEqual(cards.get_payments("Today"), {"value": 40.0, "count": 1})
			self.assertEqual(cards.get_transfers("Today"), {"value": 10.0, "count": 1})
			self.assertEqual(cards.get_expenses("Today"), {"value": 60.0})
			self.assertEqual(cards.get_gross_profit("Today"), {"value": 60.0, "percent": 60})
			self.assertEqual(
				cards.get_stock_movements("Today"), {"value": 1, "count": 1, "format": "int"}
			)

	def test_balance_metrics_ignore_the_period(self):
		with self.freeze_time(FRIDAY):
			self.assertEqual(cards.get_receivables("Today"), {"value": 350.0, "count": 2})
			self.assertEqual(cards.get_payables("Today"), {"value": 80.0, "count": 1})
			self.assertEqual(cards.get_stock_balance("Today"), {"value": 700.0, "count": 1})
			self.assertEqual(cards.get_advances("Today"), {"value": 25.0, "count": 1})

	def test_every_metric_is_whitelisted(self):
		"""get_dashboard_cards only calls whitelisted fadl_books methods."""
		for name in METRICS:
			self.assertIn(frappe.get_attr(f"fadl_books.dashboard.{name}"), frappe.whitelisted)


class IntegrationTestDashboardCards(IntegrationTestCase):
	def setUp(self):
		settings = frappe.get_single("Books Dashboard Settings")
		settings.set("cards", [])
		for row in (
			{"title": "Sales", "enabled": 1, "metric_method": "fadl_books.dashboard.get_sales", "color": "blue"},
			{"title": "Hidden", "enabled": 0, "metric_method": "fadl_books.dashboard.get_purchases"},
			{"title": "Foreign", "enabled": 1, "metric_method": "frappe.ping"},
			{"title": "Missing", "enabled": 1, "metric_method": "fadl_books.dashboard.get_nope"},
			{"title": "Stock", "enabled": 1, "metric_method": "fadl_books.dashboard.get_stock_movements", "color": "dynamic"},
		):
			settings.append("cards", row)
		settings.save()
		_invoice("Books Sales Invoice", TODAY, 100, 0)

	def test_cards_contract(self):
		with self.freeze_time(FRIDAY):
			result = cards.get_dashboard_cards("Today")

		self.assertEqual([card["title"] for card in result], ["Sales", "Foreign", "Missing", "Stock"])
		sales, foreign, missing, stock = result
		self.assertEqual((sales["value"], sales["count"]), (100.0, 1))
		self.assertEqual((sales["from_date"], sales["to_date"]), ("2026-11-20", "2026-11-20"))
		# Only whitelisted fadl_books methods run; anything else is a card without a figure.
		for card in (foreign, missing):
			self.assertIsNone(card["value"])
			self.assertEqual(card["count"], 0)
		self.assertEqual(stock["format"], "int")

	def test_custom_range_reaches_the_cards(self):
		with self.freeze_time(FRIDAY):
			result = cards.get_dashboard_cards(f"Custom:{YESTERDAY}:{TODAY}")
		self.assertEqual((result[0]["from_date"], result[0]["to_date"]), (YESTERDAY, TODAY))