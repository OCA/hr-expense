# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()

        for expense_id, move_line_values in move_line_values_by_expense.items():
            expense = self.browse(expense_id)
            if expense.sheet_id.payment_term_id:
                self._apply_payment_terms(expense, move_line_values)
            else:
                self._apply_due_date(expense, move_line_values)

        return move_line_values_by_expense

    def _apply_payment_terms(self, expense, move_line_values):
        # Locate and remove the original payable line
        payable_line = next(
            (line for line in move_line_values if line.get("date_maturity")), None
        )
        if payable_line:
            move_line_values.remove(payable_line)

        # Generate new lines based on payment terms
        payment_terms = self._prepare_payment_terms(expense, move_line_values)

        term_index = 0
        for due_date, amount in payment_terms:
            new_line = payable_line.copy()
            new_line["date_maturity"] = due_date
            new_line["debit"] = 0.0
            new_line["credit"] = amount
            move_line_values.append(new_line)
            term_index += 1

    def _prepare_payment_terms(self, expense, move_line_values):
        total_amount = sum(line["debit"] - line["credit"] for line in move_line_values)
        payment_terms = expense.sheet_id.payment_term_id.compute(
            value=total_amount,
            date_ref=expense.sheet_id.accounting_date
            or fields.Date.context_today(expense),
            currency=self.company_id.currency_id or self.env.company.currency_id,
        )
        return payment_terms

    def _apply_due_date(self, expense, move_line_values):
        for move_line in move_line_values:
            if move_line.get("date_maturity"):
                move_line["date_maturity"] = (
                    expense.sheet_id.due_date or move_line["date_maturity"]
                )
