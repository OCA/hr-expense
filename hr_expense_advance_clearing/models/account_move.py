# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _check_hr_advance_move_reconciled(self):
        """Check if the advance move lines already cleard/returned"""
        av_moves = self.filtered("line_ids.expense_id.sheet_id.advance")
        emp_advance = self.env.ref("hr_expense_advance_clearing.product_emp_advance")
        reconciled_av_move_lines = av_moves.mapped("line_ids").filtered(
            lambda l: l.product_id == emp_advance and l.matching_number
        )
        if reconciled_av_move_lines:
            raise UserError(
                _(
                    "This operation is not allowed as some advance amount was already "
                    "cleared/returned.\nPlease cancel those documents first."
                )
            )

    def button_draft(self):
        self._check_hr_advance_move_reconciled()
        return super().button_draft()

    def button_cancel(self):
        self._check_hr_advance_move_reconciled()
        return super().button_cancel()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        self._check_hr_advance_move_reconciled()
        return super()._reverse_moves(
            default_values_list=default_values_list, cancel=cancel
        )

    @api.depends(
        "line_ids.matched_debit_ids.debit_move_id.move_id.payment_id.is_matched",
        "line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual",
        "line_ids.matched_debit_ids.debit_move_id.move_id.line_ids.amount_residual_currency",
        "line_ids.matched_credit_ids.credit_move_id.move_id.payment_id.is_matched",
        "line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual",
        "line_ids.matched_credit_ids.credit_move_id.move_id.line_ids.amount_residual_currency",
        "line_ids.balance",
        "line_ids.currency_id",
        "line_ids.amount_currency",
        "line_ids.amount_residual",
        "line_ids.amount_residual_currency",
        "line_ids.payment_id.state",
        "line_ids.full_reconcile_id",
        "state",
    )
    def _compute_amount(self):
        """Compute amount residual for advance clearing case."""
        res = super()._compute_amount()
        for move in self:
            total_residual = 0.0
            total_residual_currency = 0.0
            for line in move.line_ids:
                if line.account_type not in ("asset_receivable", "liability_payable"):
                    continue
                # Line residual amount.
                clearing = line.expense_id.sheet_id.filtered(
                    lambda sheet: sheet.advance_sheet_id
                )
                if clearing:
                    # Residual amount.
                    total_residual += line.amount_residual
                    total_residual_currency += line.amount_residual_currency

            # Update amount residual for case clearing
            if total_residual and total_residual_currency:
                sign = move.direction_sign
                move.amount_residual = -sign * total_residual
                move.amount_residual_signed = total_residual_currency
        return res
