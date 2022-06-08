# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _cancel_account_move_document(self, moves):
        """ Cancel following standard odoo (posted -> draft -> cancel) """
        moves.button_draft()  # unreconciled move line
        moves.button_cancel()

    def action_cancel(self):
        move_cancel_state = self.env.company.expense_move_cancel
        moves = self.mapped("account_move_id")
        self._cancel_account_move_document(moves)
        # Reset is_refused on expense, if not cancel
        if move_cancel_state != "cancel":
            self.mapped("expense_line_ids").write({"is_refused": False})
        return self.write({"state": move_cancel_state, "account_move_id": False})


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def refuse_expense(self, reason):
        active_model = self._context.get("active_model", False)
        # Ignore state refuse if payment not config with cancel
        if (
            active_model == "account.payment"
            and self.env.company.expense_payment_cancel != "cancel"
        ):
            return
        return super().refuse_expense(reason)
