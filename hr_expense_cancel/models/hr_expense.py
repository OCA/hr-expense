# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def action_reset(self):
        """Tear down linked payments and the posted move so core's reset
        guard passes, then let super reset the expense. Runs with the
        caller's rights, as in 18.0."""
        for expense in self:
            moves = expense.account_move_id
            if not moves:
                continue
            payments = moves.reconciled_payment_ids.filtered(
                lambda p: p.state != "canceled"
            )
            self._remove_reconcile_hr_invoice(moves)
            if expense.payment_mode == "own_account":
                self._remove_move_reconcile(payments, moves)
            payments.action_draft_cancel()
            non_draft = moves.filtered(lambda m: m.state != "draft")
            if non_draft:
                non_draft.button_draft()
                non_draft.button_cancel()
            moves.with_context(force_delete=True).unlink()
        return super().action_reset()

    def _remove_reconcile_hr_invoice(self, account_moves):
        """Cancel bills made by hr_expense_invoice automatically."""
        exp_move_lines = self.env["account.move.line"].search(
            [
                (
                    "full_reconcile_id",
                    "in",
                    account_moves.line_ids.full_reconcile_id.ids,
                ),
                ("move_id", "not in", account_moves.ids),
            ]
        )
        if exp_move_lines:
            moves = exp_move_lines.move_id
            moves.button_draft()
            moves.button_cancel()

    def _remove_move_reconcile(self, payments, account_moves):
        """Unreconcile only the lines matched with the expense's own payments,
        partial reconciliations included."""
        to_unreconcile_move_lines = account_moves._get_reconciled_amls().filtered(
            lambda line: line.move_id in payments.move_id
        )
        if to_unreconcile_move_lines:
            to_unreconcile_move_lines.remove_move_reconcile()
