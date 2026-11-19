import frappe
from fadl_books import install
from frappe.tests import IntegrationTestCase

HIDDEN_FIELDS = {
	"Books Sales Invoice": ("naming_series", "debit_to", "taxes_and_charges", "taxes", "total_taxes_and_charges", "discount_after_tax"),
	"Books Purchase Invoice": ("naming_series", "credit_to", "taxes_and_charges", "taxes"),
	"Books Sales Invoice Item": ("income_account", "item_tax_template", "gst_hsn_code"),
	"Books Purchase Invoice Item": ("expense_account", "item_tax_template", "gst_hsn_code"),
	"Books Payment Entry Deduction": ("account",),
	"Books Quotation": ("taxes_and_charges", "taxes"),
	"Books Quotation Item": ("item_tax_template", "gst_hsn_code"),
	"Books Item": ("item_type", "is_stock_item", "taxes"),
}


class IntegrationTestInstallCustomizations(IntegrationTestCase):
	def setUp(self):
		if not frappe.db.exists("Currency", "RUB"):
			frappe.get_doc({"doctype": "Currency", "currency_name": "RUB"}).insert()
		install.execute()

	def test_execute_is_idempotent(self):
		install.execute()  # a second run must not raise

	def test_rub_currency_is_set_up(self):
		currency = frappe.get_doc("Currency", "RUB")
		self.assertEqual(currency.symbol, "₽")
		self.assertEqual(currency.symbol_on_right, 1)

	def test_fields_are_hidden(self):
		for doctype, fieldnames in HIDDEN_FIELDS.items():
			meta = frappe.get_meta(doctype)
			for fieldname in fieldnames:
				field = meta.get_field(fieldname)
				self.assertIsNotNone(field, f"{doctype}.{fieldname} is gone")
				self.assertEqual(field.hidden, 1, f"{doctype}.{fieldname} is visible again")

	def test_sections_are_collapsed(self):
		for doctype in ("Books Sales Invoice", "Books Purchase Invoice", "Books Quotation"):
			self.assertEqual(frappe.get_meta(doctype).get_field("taxes_section").depends_on, "eval:0")
		item = frappe.get_meta("Books Item")
		self.assertEqual(item.get_field("inventory_section_break_15").depends_on, "eval:0")
		self.assertEqual(item.get_field("taxes_section_break").depends_on, "eval:0")
		self.assertEqual(item.get_field("is_stock_item").default, "1")

	def test_transfer_accounts_stay_visible_only_for_transfer(self):
		meta = frappe.get_meta("Books Payment Entry")
		for fieldname in ("paid_from", "paid_to"):
			self.assertEqual(
				meta.get_field(fieldname).depends_on,
				"eval:doc.payment_type != 'Internal Transfer'",
			)

	def test_posting_date_ends_the_main_tab(self):
		for doctype, fieldname in install.DATE_AT_END.items():
			fields = frappe.get_meta(doctype).fields
			names = [df.fieldname for df in fields]
			if fieldname not in names:
				self.fail(f"{doctype}.{fieldname} is gone")
			tab = next((i for i, df in enumerate(fields) if df.fieldtype == "Tab Break"), len(fields))
			self.assertEqual(names.index(fieldname), tab - 1, f"{doctype}: date is not at the main tab's end")