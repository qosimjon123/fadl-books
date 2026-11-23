import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import flt, nowdate
from frappe_books.tests.accounting import (
	ledger_entries,
	make_account,
	make_customer,
	make_mode_of_payment,
	make_supplier,
)

from fadl_books.fadl_books.doctype.books_loan.books_loan import make_repayment
from fadl_books.install import add_loan_accounts

LOAN_ACCOUNTS = (
	("Loans Given", "Loans and Advances (Assets)", "Asset"),
	("Loans Taken", "Loans (Liabilities)", "Liability"),
)


class IntegrationTestLoans(IntegrationTestCase):
	def setUp(self):
		add_loan_accounts()
		self.cash = make_account("Loans Cash", account_type="Cash")
		self.mode = make_mode_of_payment("Loans Cash", "Cash", self.cash.name)
		receivable = make_account("Loans Debtors", account_type="Receivable")
		payable = make_account("Loans Creditors", account_type="Payable")
		self.customer = make_customer(receivable.name)
		self.supplier = make_supplier(payable.name)

	def _loan(self, direction, party_type, party, amount=1000):
		return frappe.get_doc(
			{
				"doctype": "Books Loan",
				"direction": direction,
				"party_type": party_type,
				"party": party,
				"amount": amount,
				"posting_date": nowdate(),
				"mode_of_payment": self.mode.name,
			}
		).insert()

	def _repayment(self, loan, amount):
		repayment = make_repayment(loan.name)
		repayment.amount = amount
		repayment.insert()
		repayment.submit()
		return repayment

	def test_loan_accounts_are_untyped_leaves(self):
		add_loan_accounts()  # a second call must not duplicate them
		for name, parent, root in LOAN_ACCOUNTS:
			account = frappe.get_doc("Books Account", name)
			self.assertEqual(account.parent_account, parent)
			self.assertEqual(account.root_type, root)
			self.assertIn(account.account_type, ("", None))
			self.assertFalse(account.is_group)

	def test_lend_posts_and_repayment_reverses(self):
		loan = self._loan("We Lend", "Books Customer", self.customer.name)
		loan.submit()
		loan.reload()
		self.assertEqual(flt(loan.outstanding_amount), 1000)
		self.assertTrue(loan.journal_entry)

		entries = ledger_entries("Books Journal Entry", loan.journal_entry)
		self.assertCountEqual(
			[(entry.account, entry.debit, entry.credit) for entry in entries],
			[("Loans Given", 1000, 0), (self.cash.name, 0, 1000)],
		)
		party_row = frappe.db.get_value(
			"Books GL Entry",
			{"voucher_no": loan.journal_entry, "account": "Loans Given"},
			["party_type", "party"],
			as_dict=True,
		)
		self.assertEqual((party_row.party_type, party_row.party), ("Books Customer", self.customer.name))

		repayment = self._repayment(loan, 400)
		loan.reload()
		self.assertEqual(flt(loan.outstanding_amount), 600)
		self.assertEqual(repayment.company, loan.company)

		repayment.cancel()
		loan.reload()
		self.assertEqual(flt(loan.outstanding_amount), 1000)
		self.assertTrue(
			all(
				entry.is_cancelled for entry in ledger_entries("Books Journal Entry", repayment.journal_entry)
			)
		)

		loan.cancel()
		loan.reload()
		self.assertEqual(flt(loan.outstanding_amount), 0)
		self.assertTrue(
			all(entry.is_cancelled for entry in ledger_entries("Books Journal Entry", loan.journal_entry))
		)

	def test_borrow_posts_the_other_way(self):
		loan = self._loan("We Borrow", "Books Supplier", self.supplier.name)
		loan.submit()
		loan.reload()

		entries = ledger_entries("Books Journal Entry", loan.journal_entry)
		self.assertCountEqual(
			[(entry.account, entry.debit, entry.credit) for entry in entries],
			[(self.cash.name, 1000, 0), ("Loans Taken", 0, 1000)],
		)

		self._repayment(loan, 1000)
		loan.reload()
		self.assertEqual(flt(loan.outstanding_amount), 0)

	def test_mapper_prefills_the_outstanding(self):
		loan = self._loan("We Lend", "Books Customer", self.customer.name)
		loan.db_set("posting_date", "2026-01-01")
		loan.submit()
		self._repayment(loan, 300)
		loan.reload()

		repayment = make_repayment(loan.name)
		self.assertEqual(repayment.loan, loan.name)
		self.assertEqual(flt(repayment.amount), 700)
		self.assertEqual(repayment.mode_of_payment, self.mode.name)
		# A repayment is dated when it is made, not when the loan was.
		self.assertEqual(str(repayment.posting_date), nowdate())

	def test_repayment_cannot_exceed_outstanding(self):
		loan = self._loan("We Lend", "Books Customer", self.customer.name)
		loan.submit()
		repayment = make_repayment(loan.name)
		repayment.amount = 1500
		self.assertRaises(frappe.ValidationError, repayment.insert)

	def test_fully_repaid_loan_maps_no_repayment(self):
		loan = self._loan("We Lend", "Books Customer", self.customer.name)
		loan.submit()
		self._repayment(loan, 1000)
		self.assertRaises(frappe.ValidationError, make_repayment, loan.name)

	def test_full_repayment_can_be_cancelled(self):
		loan = self._loan("We Lend", "Books Customer", self.customer.name)
		loan.submit()
		repayment = self._repayment(loan, 1000)
		loan.reload()
		self.assertEqual(flt(loan.outstanding_amount), 0)

		repayment.cancel()
		loan.reload()
		self.assertEqual(flt(loan.outstanding_amount), 1000)

	def test_loan_cancel_waits_for_repayments(self):
		loan = self._loan("We Lend", "Books Customer", self.customer.name)
		loan.submit()
		self._repayment(loan, 400)
		self.assertRaises(frappe.ValidationError, loan.cancel)
		loan.reload()
		self.assertEqual(loan.docstatus, 1)

	def test_repayment_mapper_override_is_registered(self):
		synthetic = "frappe_books.fadl_books.doctype.books_loan.books_loan.make_repayment"
		path = frappe.override_whitelisted_method(synthetic)
		self.assertEqual(path, "fadl_books.fadl_books.doctype.books_loan.books_loan.make_repayment")
		self.assertIn(frappe.get_attr(path), frappe.whitelisted)
