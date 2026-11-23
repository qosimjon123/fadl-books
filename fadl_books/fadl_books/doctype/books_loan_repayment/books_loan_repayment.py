# Copyright (c) 2026, FadlTech team and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from fadl_books.fadl_books.doctype.books_loan.books_loan import post_loan_journal


class BooksLoanRepayment(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		amount: DF.Currency
		company: DF.Link | None
		journal_entry: DF.Link | None
		loan: DF.Link
		mode_of_payment: DF.Link | None
		posting_date: DF.Date
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Loan Repayment"

	def validate(self):
		loan = frappe.get_doc("Books Loan", self.loan)
		loan.check_permission("read")
		# Cancel runs validate again, when the outstanding no longer holds this amount.
		if self.docstatus != 2:
			if loan.docstatus != 1:
				frappe.throw(_("Only a submitted loan can be repaid."))
			if flt(self.amount) <= 0:
				frappe.throw(_("Amount must be greater than zero."))
			if flt(self.amount) > flt(loan.outstanding_amount):
				frappe.throw(_("Amount exceeds the loan's outstanding amount."))
		self.company = loan.company
		self.mode_of_payment = self.mode_of_payment or loan.mode_of_payment

	def on_submit(self):
		loan = frappe.get_doc("Books Loan", self.loan, for_update=True)
		outstanding = flt(loan.outstanding_amount)
		if flt(self.amount) > outstanding:
			frappe.throw(_("Amount exceeds the loan's outstanding amount."))
		entry = post_loan_journal(loan, self.amount, self.posting_date, reverse=True)
		frappe.db.set_value(self.doctype, self.name, "journal_entry", entry.name)
		frappe.db.set_value("Books Loan", loan.name, "outstanding_amount", outstanding - flt(self.amount))

	def on_cancel(self):
		if self.journal_entry:
			frappe.get_doc("Books Journal Entry", self.journal_entry).cancel()
		outstanding = frappe.db.get_value("Books Loan", self.loan, "outstanding_amount")
		frappe.db.set_value(
			"Books Loan", self.loan, "outstanding_amount", flt(outstanding) + flt(self.amount)
		)
