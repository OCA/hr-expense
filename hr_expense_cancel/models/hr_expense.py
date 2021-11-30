# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_cancel(self):
        policy_cancel = self.env.company.expense_cancel_policy
        cancel_state_to = self.env.company.expense_cancel_state
        for sheet in self:
            account_move = sheet.account_move_id
            # Unlink Journal Entry on Expense Sheet
            sheet.account_move_id = False
            if account_move.exists():
                # Cancel move
                if account_move.state != "draft":
                    account_move.button_cancel()
                if policy_cancel == "unlink":
                    account_move.with_context(force_delete=True).unlink()
        return self.write({"state": cancel_state_to})
