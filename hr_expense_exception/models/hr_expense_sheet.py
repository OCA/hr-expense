# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class HRExpenseSheet(models.Model):
    _inherit = ["hr.expense.sheet", "base.exception"]
    _name = "hr.expense.sheet"
    _order = "main_exception_id asc, accounting_date desc, id desc"

    @api.model
    def test_all_draft_expenses(self):
        expense_set = self.search([("state", "=", "draft")])
        expense_set.detect_exceptions()
        return True

    @api.model
    def _reverse_field(self):
        return "expense_sheet_ids"

    def detect_exceptions(self):
        all_exceptions = super().detect_exceptions()
        lines = self.mapped("expense_line_ids")
        all_exceptions += lines.detect_exceptions()
        return all_exceptions

    @api.constrains("ignore_exception", "expense_line_ids", "state")
    def expense_check_exception(self):
        expenses = self.filtered(lambda s: s.state == "submit")
        if expenses:
            expenses._check_exception()

    @api.onchange("expense_line_ids")
    def onchange_ignore_exception(self):
        if self.state == "submit":
            self.ignore_exception = False

    def action_submit_sheet(self):
        if self.detect_exceptions() and not self.ignore_exception:
            return self._popup_exceptions()
        return super().action_submit_sheet()

    def reset_expense_sheets(self):
        res = super().reset_expense_sheets()
        for expense in self:
            expense.exception_ids = False
            expense.main_exception_id = False
            expense.ignore_exception = False
        return res

    @api.model
    def _get_popup_action(self):
        action = self.env.ref(
            "hr_expense_exception.action_expense_sheet_exception_confirm"
        )
        return action
