import json

import frappe


def execute():
	setup_currency()
	hide_naming_series_fields()
	hide_default_account_fields()
	hide_tax_fields()
	simplify_item_form()
	tidy_date_fields()
	add_stock_receipt_basis()
	tidy_stock_entry_rows()
	

def setup_currency():
	"""RUB is created at site install without a symbol, so set ₽ here."""
	currency = frappe.get_doc("Currency", "RUB")
	currency.symbol = "₽"
	currency.fraction = "коп."
	currency.symbol_on_right = 1
	currency.save()


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

def add_stock_receipt_basis():
	"""Начальный остаток и излишки — оба Material Receipt. Селект называет, какой
	именно приход: плитки фильтруют список и предзаполняют форму, ручной приход
	по умолчанию считается излишком.

	ignore_validate=True пропускает проверку меты при создании поля — иначе она
	спотыкается о скрытый обязательный naming_series (наш hide_naming_series_fields).
	Сам naming_series не трогаем."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"Books Stock Entry": [
				{
					"fieldname": "receipt_basis",
					"label": "Receipt Basis",
					"fieldtype": "Select",
					"options": "\nOpening Stock\nStock Surplus",
					"default": "",
					"insert_after": "purpose",
					"hidden": 0,
					"depends_on": "eval:doc.purpose == 'Material Receipt'",
					"translatable": 0,
				}
			]
		},
		ignore_validate=True,
		update=True,
	)


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