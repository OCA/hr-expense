# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _check_hr_advance_move_reconciled(self):
        """Check if the advance move lines already cleard/returned"""
        av_moves = self.filtered("line_ids.expense_id.sheet_id.advance")
        emp_advance = self.env.ref("hr_expense_advance_clearing.product_emp_advance")
        reconciled_av_move_lines = av_moves.mapped("line_ids").filtered(
            lambda line: line.product_id == emp_advance and line.matching_number
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

    def action_force_register_payment(self):
        """
        Odoo core does not allow register payment with type 'entry'.
        However, a payment can be registered when clearing a document,
        provided the amount cleared exceeds the advance payment.
        """
        if all(
            m.expense_sheet_id.advance_sheet_id and m.move_type == "entry" for m in self
        ):
            return self.line_ids.action_register_payment(ctx={"expense_clearing": 1})
        return super().action_force_register_payment()
