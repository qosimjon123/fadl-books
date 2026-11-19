# Copyright (c) 2026, FadlTech team and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class BooksDashboardCard(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		color: DF.Literal["blue", "green", "red", "gray", "orange", "dynamic"]
		enabled: DF.Check
		icon: DF.Data | None
		metric_method: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		route: DF.Data | None
		title: DF.Data
	# end: auto-generated types

	_DOCTYPE_NAME = "Books Dashboard Card"
