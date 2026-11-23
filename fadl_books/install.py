import json

import frappe
from frappe_books.coa import ensure_account


def execute():
	setup_currency()
	hide_naming_series_fields()
	hide_default_account_fields()
	hide_tax_fields()
	simplify_item_form()
	tidy_date_fields()
	tidy_stock_entry_rows()
	tidy_invoice_rows()
	add_loan_accounts()
	add_dashboard_cards()
	rename_default_records()
	setup_language()


def add_loan_accounts():
	"""Leaf accounts for loans, with no account_type so the journal may carry any party type.
	The native helper is idempotent and makes the parent group when the chart has none."""
	ensure_account("Loans Given", "Loans and Advances (Assets)", "Asset")
	ensure_account("Loans Taken", "Loans (Liabilities)", "Liability")


def setup_currency():
	"""RUB is created at site install without a symbol, so set ₽ here."""
	currency = frappe.get_doc("Currency", "RUB")
	currency.symbol = "₽"
	currency.fraction = "коп."
	currency.symbol_on_right = 1
	currency.save()


def setup_language():
	"""Russian is created at site install without a flag, so set 🇷🇺 here."""
	language = frappe.get_doc("Language", "ru")
	language.enabled = 1
	language.save()


def hide_naming_series_fields():
	"""Safe to hide: SeriesNamingMixin fills naming_series from Books Defaults on save.
	For simpllicty for mobile users, we don't want to show the field in the form."""
	frappe.make_property_setter(
		{
			"fieldname": "naming_series",
			"property": "hidden",
			"value": 1,
			"property_type": "Check",
		},
		validate_fields_for_doctype=False,
	)


def _setter(doctype, fieldname, prop, value, property_type):
	frappe.make_property_setter(
		{
			"doctype": doctype,
			"fieldname": fieldname,
			"property": prop,
			"value": value,
			"property_type": property_type,
		},
		validate_fields_for_doctype=False,
	)


def hide_default_account_fields():
	"""Safe to hide: controllers fill these from party, item and company defaults.
	Payment accounts stay visible for Internal Transfer: its destination is chosen by hand."""
	for doctype, fieldname in (
		("Books Sales Invoice", "debit_to"),
		("Books Purchase Invoice", "credit_to"),
		("Books Sales Invoice Item", "income_account"),
		("Books Purchase Invoice Item", "expense_account"),
		("Books Payment Entry Deduction", "account"),
	):
		_setter(doctype, fieldname, "hidden", 1, "Check")
	for fieldname in ("paid_from", "paid_to"):
		_setter(
			"Books Payment Entry",
			fieldname,
			"depends_on",
			"eval:doc.payment_type != 'Internal Transfer'",
			"Code",
		)


def hide_tax_fields():
	"""No tax templates exist on this site, so taxes compute to zero; the fields are noise.
	A template added later still auto-applies to new documents (taxes.py fills it in)."""
	for doctype in ("Books Sales Invoice", "Books Purchase Invoice", "Books Quotation"):
		# eval:0 on the break hides the whole Taxes section, header included, in Books and Desk.
		_setter(doctype, "taxes_section", "depends_on", "eval:0", "Code")
		for fieldname in ("taxes_and_charges", "taxes", "total_taxes_and_charges", "discount_after_tax"):
			_setter(doctype, fieldname, "hidden", 1, "Check")
	for doctype in ("Books Sales Invoice Item", "Books Purchase Invoice Item", "Books Quotation Item"):
		for fieldname in ("item_tax_template", "gst_hsn_code"):
			_setter(doctype, fieldname, "hidden", 1, "Check")


DATE_AT_END = {
	"Books Sales Invoice": "posting_date",
	"Books Purchase Invoice": "posting_date",
	"Books Payment Entry": "posting_date",
	"Books Journal Entry": "posting_date",
	"Books Delivery Note": "posting_date",
	"Books Purchase Receipt": "posting_date",
	"Books Stock Entry": "posting_date",
	"Books Quotation": "transaction_date",
}


def tidy_date_fields():
	"""Dates default to Today, so they go to the form's end; never hidden.
	The end means the end of the MAIN tab: past the first Tab Break lies the
	service Settings tab, and a date there costs an extra tap on mobile.
	Dates without a default (reference, clearance, cheque) stay put.
	Order is overridden the way Customize Form does it: a DocType-level field_order
	setter, because meta.sort_fields() renumbers per-field idx and ignores such setters."""
	for doctype, fieldname in DATE_AT_END.items():
		fields = frappe.get_meta(doctype).fields
		order = [df.fieldname for df in fields]
		if fieldname not in order:
			continue
		order.remove(fieldname)
		tab = next(
			(i for i, df in enumerate(fields) if df.fieldtype == "Tab Break"),
			len(fields),
		)
		order.insert(sum(1 for df in fields[:tab] if df.fieldname != fieldname), fieldname)
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocType",
				"property": "field_order",
				"value": json.dumps(order),
			},
			validate_fields_for_doctype=False,
		)


def simplify_item_form():
	"""We sell stocked products only: type and the inventory block are noise.
	The item's own Taxes table goes the way of invoice taxes."""
	_setter("Books Item", "item_type", "hidden", 1, "Check")
	_setter("Books Item", "is_stock_item", "default", "1", "Data")
	_setter("Books Item", "is_stock_item", "hidden", 1, "Check")
	_setter("Books Item", "inventory_section_break_15", "depends_on", "eval:0", "Code")
	_setter("Books Item", "taxes_section_break", "depends_on", "eval:0", "Code")
	_setter("Books Item", "taxes", "hidden", 1, "Check")
	_setter("Books Item", "item_code", "in_list_view", 1, "Check")


def tidy_stock_entry_rows():
	"""Строка склада: порядок товар → склады → кол-во → цена → ед.изм. →
	остальное как было, партия и серия в конце; ед.изм. видна в списке.
	Мёртвый склад скрыт: у прихода нет отправителя, у списания нет получателя;
	в комплектации направление задаёт заполненный склад (mutual exclusion).
	Порядок — DocType-level field_order: meta.sort_fields перенумеровывает
	пофилдовые idx и игнорирует такие сеттеры."""
	order = [
		"item_code",
		"item_name",
		"s_warehouse",
		"t_warehouse",
		"qty",
		"basic_rate",
		"uom",
		"amount",
		"conversion_factor",
		"stock_uom",
		"transfer_qty",
		"batch_no",
		"serial_no",
	]
	frappe.make_property_setter(
		{
			"doctype": "Books Stock Entry Detail",
			"doctype_or_field": "DocType",
			"property": "field_order",
			"value": json.dumps(order),
		},
		validate_fields_for_doctype=False,
	)
	_setter(
		"Books Stock Entry Detail",
		"s_warehouse",
		"depends_on",
		"eval:parent.purpose != 'Material Receipt' && (parent.purpose != 'Repack' || !doc.t_warehouse || doc.s_warehouse)",
		"Code",
	)
	_setter(
		"Books Stock Entry Detail",
		"t_warehouse",
		"depends_on",
		"eval:parent.purpose != 'Material Issue' && (parent.purpose != 'Repack' || !doc.s_warehouse || doc.t_warehouse)",
		"Code",
	)


def tidy_invoice_rows():
	"""Строка счёта и предложения: товар → кол-во → цена → ед.изм. → коэффициент →
	базовая ед.изм. → скидка % → скидка суммой → сумма → партия → серия,
	остальное в конце в прежнем порядке.
	Порядок — DocType-level field_order: meta.sort_fields перенумеровывает
	пофилдовые idx и игнорирует такие сеттеры."""
	priority = [
		"item_code",
		"qty",
		"price_list_rate",
		"uom",
		"amount",
		"conversion_factor",
		"stock_uom",
		"discount_percentage",
		"discount_amount",
		"batch_no",
		"serial_no",
	]
	for doctype in (
		"Books Sales Invoice Item",
		"Books Purchase Invoice Item",
		"Books Quotation Item",
	):
		fields = [df.fieldname for df in frappe.get_meta(doctype).fields]
		head = [f for f in priority if f in fields]
		order = head + [f for f in fields if f not in head]
		frappe.make_property_setter(
			{
				"doctype": doctype,
				"doctype_or_field": "DocType",
				"property": "field_order",
				"value": json.dumps(order),
			},
			validate_fields_for_doctype=False,
		)


# The dashboard card set in the user's priority order; titles as the dashboard shows them.
DASHBOARD_CARDS = [
	{
		"title": "Продажи",
		"color": "blue",
		"metric_method": "fadl_books.dashboard.get_sales",
		"route": "/list/SalesInvoice",
	},
	{
		"title": "Валовая прибыль",
		"color": "dynamic",
		"metric_method": "fadl_books.dashboard.get_gross_profit",
		"route": "/report/ProfitAndLoss",
	},
	{
		"title": "Поступления",
		"color": "green",
		"metric_method": "fadl_books.dashboard.get_receipts",
		"route": '/list/PaymentEntry?filters=[["payment_type","=","Receive"]]',
	},
	{
		"title": "Остатки",
		"color": "blue",
		"metric_method": "fadl_books.dashboard.get_stock_balance",
		"route": "/report/StockBalance",
	},
	{
		"title": "Мы должны",
		"color": "red",
		"metric_method": "fadl_books.dashboard.get_payables",
		"route": '/list/PurchaseInvoice?filters=[["docstatus","=",1],["outstanding_amount","!=",0]]',
	},
	{
		"title": "Нам должны",
		"color": "blue",
		"metric_method": "fadl_books.dashboard.get_receivables",
		"route": '/list/SalesInvoice?filters=[["docstatus","=",1],["outstanding_amount","!=",0]]',
	},
	{
		"title": "Расходы",
		"color": "orange",
		"metric_method": "fadl_books.dashboard.get_expenses",
		"route": "/report/ProfitAndLoss",
	},
	{
		"title": "Выплаты",
		"color": "orange",
		"metric_method": "fadl_books.dashboard.get_payments",
		"route": '/list/PaymentEntry?filters=[["payment_type","=","Pay"]]',
	},
	{
		"title": "Закупки",
		"color": "orange",
		"metric_method": "fadl_books.dashboard.get_purchases",
		"route": "/list/PurchaseInvoice",
	},
	{
		"title": "Авансы",
		"color": "gray",
		"metric_method": "fadl_books.dashboard.get_advances",
		"route": '/list/PaymentEntry?filters=[["docstatus","=",1],["unallocated_amount","!=",0]]',
	},
	{
		"title": "Займы: нам должны",
		"color": "blue",
		"metric_method": "fadl_books.dashboard.get_loans_given",
		"route": '/list/FadlLoan?filters=[["docstatus","=",1],["direction","=","We Lend"],["outstanding_amount","!=",0]]',
	},
	{
		"title": "Займы: мы должны",
		"color": "orange",
		"metric_method": "fadl_books.dashboard.get_loans_taken",
		"route": '/list/FadlLoan?filters=[["docstatus","=",1],["direction","=","We Borrow"],["outstanding_amount","!=",0]]',
	},
	{
		"title": "Переводы",
		"color": "gray",
		"metric_method": "fadl_books.dashboard.get_transfers",
		"route": '/list/PaymentEntry?filters=[["payment_type","=","Internal Transfer"]]',
	},
	{
		"title": "Движения товаров",
		"color": "gray",
		"metric_method": "fadl_books.dashboard.get_stock_movements",
		"route": "/report/StockLedger",
	},
]


def add_dashboard_cards():
	"""The dashboard card set, recreated after a reinstall wipes the site's data.
	Idempotent by metric_method: existing rows keep their values, missing ones are
	appended; when anything was added the default set takes its priority order again."""
	settings = frappe.get_single("Books Dashboard Settings")
	existing = {row.metric_method for row in settings.cards}
	changed = False
	for card in DASHBOARD_CARDS:
		if card["metric_method"] not in existing:
			settings.append("cards", dict(card, enabled=1))
			changed = True
	# Loans are separate cards now — the old one keeps only advances.
	for row in settings.cards:
		if row.metric_method == "fadl_books.dashboard.get_advances" and row.title == "Займы и авансы":
			row.title = "Авансы"
			changed = True
	if changed:
		order = {card["metric_method"]: i for i, card in enumerate(DASHBOARD_CARDS)}
		settings.cards.sort(key=lambda row: order.get(row.metric_method, len(order)))
		for idx, row in enumerate(settings.cards, start=1):
			row.idx = idx
		settings.save()


# Setup seeds English UOMs and the Stores warehouse; the shop works in Russian.
DEFAULT_RENAMES = {
	"Books UOM": {
		"Unit": "Шт",
		"Kg": "Кг",  # noqa: RUF001 -- Cyrillic UOM name, intentional
		"Gram": "Грамм",
		"Meter": "Метр",
		"Hour": "Час",
		"Day": "День",
	},
	"Books Warehouse": {"Stores": "Магазин"},
}


def rename_default_records():
	"""These are records, not labels: property setters cannot rename them.
	rename_doc relinks every document; skipped once renamed or if the target exists."""
	for doctype, names in DEFAULT_RENAMES.items():
		for old, new in names.items():
			if frappe.db.exists(doctype, old) and not frappe.db.exists(doctype, new):
				frappe.rename_doc(doctype, old, new)
