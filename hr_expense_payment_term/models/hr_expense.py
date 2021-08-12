# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    def _compute_payment_term(self, ml):
        self.ensure_one()
        if self.sheet_id.expense_payment_term_id:
            if self.currency_id == self.company_id.currency_id:
                # Single-currency.
                to_compute = self.sheet_id.expense_payment_term_id.compute(
                    ml["credit"],
                    date_ref=ml["date_maturity"],
                    currency=self.company_id.currency_id,
                )
            else:
                # Multi-currencies.
                to_compute = self.expense_payment_term_id.compute(
                    ml["amount_currency"],
                    date_ref=ml["date_maturity"],
                    currency=self.currency_id,
                )
            ml["date_maturity"] = fields.Date.from_string(to_compute[0][0])
        else:
            ml["date_maturity"] = self.sheet_id.expense_date_due or ml["date_maturity"]
        return ml

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            for ml in move_line_values_by_expense[expense.id]:
                if not ml.get("product_id") and ml.get("credit"):
                    # compute due date on move line by expense due date
                    ml = expense._compute_payment_term(ml)
                    expense.sheet_id.expense_date_due = ml["date_maturity"]
        return move_line_values_by_expense
