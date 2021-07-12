# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ExceptionRule(models.Model):
    _inherit = "exception.rule"

    expense_sheet_ids = fields.Many2many(
        comodel_name="hr.expense.sheet", string="Expense Reports"
    )
    model = fields.Selection(
        selection_add=[
            ("hr.expense.sheet", "Expense Report"),
            ("hr.expense", "Expense"),
        ],
        ondelete={"hr.expense.sheet": "cascade", "hr.expense": "cascade"},
    )
