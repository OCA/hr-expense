# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_cancel(self):
        for sheet in self:
            account_moves = sheet.account_move_ids
            sheet.account_move_ids = False
            payments = sheet.payment_ids.filtered(lambda line: line.state != "cancel")
            # case : cancel invoice from hr_expense
            self._remove_reconcile_hr_invoice(account_moves)
            # If the sheet is paid then remove payments
            if sheet.state in ("done", "approve"):
                if sheet.expense_line_ids[:1].payment_mode == "own_account":
                    self._remove_move_reconcile(payments, account_moves)
                payments.action_draft_cancel()
            # Deleting the Journal entry if in the previous steps
            # (if the expense sheet is paid and payment_mode == 'own_account')
            # it has not been deleted
            if account_moves.exists():
                moves_to_cancel = account_moves.filtered(
                    lambda move: move.state != "draft"
                )
                if moves_to_cancel:
                    moves_to_cancel.button_cancel()
                account_moves.with_context(force_delete=True).unlink()
            sheet.state = "submit"

    def _remove_reconcile_hr_invoice(self, account_moves):
        """Cancel invoice made by hr_expense_invoice module automatically"""
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
        # set state to cancel
        if exp_move_lines:
            moves = exp_move_lines.move_id
            moves.button_draft()
            moves.button_cancel()

    def _remove_move_reconcile(self, payments, account_moves):
        """Delete only reconciliations made with the payments generated
        by hr_expense module automatically"""
        to_unreconcile_move_lines = self.env["account.move.line"].search(
            [
                (
                    "full_reconcile_id",
                    "in",
                    account_moves.line_ids.full_reconcile_id.ids,
                ),
                ("move_id", "in", payments.move_id.ids),
            ]
        )
        if to_unreconcile_move_lines:
            to_unreconcile_move_lines.remove_move_reconcile()
