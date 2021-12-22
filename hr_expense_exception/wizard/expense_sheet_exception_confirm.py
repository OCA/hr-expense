# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ExpenseSheetExceptionConfirm(models.TransientModel):
    _name = "expense.sheet.exception.confirm"
    _description = "Expense report exception wizard"
    _inherit = ["exception.rule.confirm"]

    related_model_id = fields.Many2one("hr.expense.sheet", "Expense Report")

    def action_confirm(self):
        self.ensure_one()
        if self.ignore:
            self.related_model_id.reset_expense_sheets()
            self.related_model_id.ignore_exception = True
            self.related_model_id.action_submit_sheet()
        return super().action_confirm()
