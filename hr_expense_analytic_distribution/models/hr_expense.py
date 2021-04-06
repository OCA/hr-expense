# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _get_account_move_line_values(self):
        res = super()._get_account_move_line_values()
        for expense in self.filtered("sheet_id.expense_distribution_ids"):
            expense_move_lines = []
            for orig_move_line in res[expense.id]:
                orig_amount = orig_move_line["amount_currency"]
                total_perc = 0.0
                total_amount = 0.0
                for dis in expense.sheet_id.expense_distribution_ids.sorted(
                    "percentage"
                ):
                    total_perc += dis.percentage
                    if total_perc == 100.0:
                        new_amount = orig_amount - total_amount
                    else:
                        new_amount = orig_amount * (dis.percentage / 100)
                    new_amount = expense.currency_id.round(new_amount)
                    total_amount += new_amount

                    move_line = dict(orig_move_line)
                    move_line.update(
                        {
                            "analytic_account_id": dis.analytic_account_id.id,
                            "amount_currency": new_amount,
                            "debit": new_amount if new_amount > 0 else 0.0,
                            "credit": abs(new_amount) if new_amount < 0 else 0.0,
                        }
                    )
                    expense_move_lines.append(move_line)
            res[expense.id] = expense_move_lines
        return res
