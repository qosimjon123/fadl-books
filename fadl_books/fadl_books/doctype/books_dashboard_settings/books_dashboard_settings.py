# Copyright (c) 2026, FadlTech team and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksDashboardSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from fadl_books.fadl_books.doctype.books_dashboard_card.books_dashboard_card import BooksDashboardCard
		from frappe.types import DF

		cards: DF.Table[BooksDashboardCard]
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Dashboard Settings"
