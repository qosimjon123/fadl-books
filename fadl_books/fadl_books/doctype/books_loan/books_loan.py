# Copyright (c) 2026, FadlTech team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt
from frappe_books.accounting.accounts import mode_of_payment_account
from frappe_books.company import default_company

# Empty account_type on these leaves lets the journal carry any party type,
# so one account serves customers and suppliers alike.
LOAN_ACCOUNTS = {"We Lend": "Loans Given", "We Borrow": "Loans Taken"}


class BooksLoan(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		company: DF.Link | None
		direction: DF.Literal["We Lend", "We Borrow"]
		journal_entry: DF.Link | None
		mode_of_payment: DF.Link | None
		outstanding_amount: DF.Currency
		party: DF.DynamicLink
		party_type: DF.Literal["Books Customer", "Books Supplier"]
		posting_date: DF.Date
		remark: DF.SmallText | None
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Loan"

	def validate(self):
		self.company = self.company or default_company()
		self.mode_of_payment = self.mode_of_payment or "Cash"
		if flt(self.amount) <= 0:
			frappe.throw(_("Amount must be greater than zero."))
		if self.docstatus == 0:
			self.outstanding_amount = self.amount

	def before_submit(self):
		self.outstanding_amount = self.amount

	def on_submit(self):
		entry = post_loan_journal(self, self.amount, self.posting_date)
		frappe.db.set_value(self.doctype, self.name, "journal_entry", entry.name)

	def on_cancel(self):
		if frappe.db.exists("Books Loan Repayment", {"loan": self.name, "docstatus": 1}):
			frappe.throw(_("Cancel this loan's repayments first."))
		if self.journal_entry:
			frappe.get_doc("Books Journal Entry", self.journal_entry).cancel()
		frappe.db.set_value(self.doctype, self.name, "outstanding_amount", 0)


def post_loan_journal(loan, amount, posting_date, reverse=False):
	"""Post the loan (or its repayment, reversed) as a standard journal entry."""
	loan_account = LOAN_ACCOUNTS[loan.direction]
	cash_account = mode_of_payment_account(loan.mode_of_payment)
	if not cash_account:
		frappe.throw(_("Set a default account for mode of payment {0}.").format(loan.mode_of_payment))

	amount = flt(amount)
	# Lending sends money out: debit the loan account. Repayment reverses it.
	loan_debit = (loan.direction == "We Lend") != bool(reverse)
	loan_row = {"account": loan_account, "party_type": loan.party_type, "party": loan.party}
	cash_row = {"account": cash_account}
	if loan_debit:
		loan_row["debit_in_account_currency"] = amount
		cash_row["credit_in_account_currency"] = amount
	else:
		loan_row["credit_in_account_currency"] = amount
		cash_row["debit_in_account_currency"] = amount

	entry = frappe.get_doc(
		{
			"doctype": "Books Journal Entry",
			"voucher_type": "Journal Entry",
			"company": loan.company,
			"posting_date": posting_date,
			"user_remark": f"{loan.name}: {loan.remark or ''}".strip(": "),
			"accounts": [loan_row, cash_row],
		}
	).insert(ignore_permissions=True)
	entry.submit()
	return entry


@frappe.whitelist()
def make_repayment(source_name: str):
	return get_mapped_doc(
		"Books Loan",
		source_name,
		{
			"Books Loan": {
				"doctype": "Books Loan Repayment",
				"validation": {"docstatus": ["=", 1]},
				# A repayment is dated when it is made, for what is left to repay.
				"field_no_map": ["posting_date", "amount"],
			},
		},
		postprocess=_fill_repayment,
	)


def _fill_repayment(loan, repayment):
	outstanding = flt(loan.outstanding_amount)
	if outstanding <= 0:
		frappe.throw(_("Loan {0} is already repaid.").format(loan.name))
	repayment.amount = outstanding
	repayment.mode_of_payment = loan.mode_of_payment
