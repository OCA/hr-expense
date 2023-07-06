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

    # @api.depends('expense_sheet_id.advance_sheet_id')
    # def _compute_payment_state(self):
    #     advance_paid = self.filtered(lambda m: m.expense_sheet_id.advance_sheet_id != False)
    #     for move in advance_paid:
    #         move.payment_state = move._get_invoice_in_payment_state()
    #     super(AccountMove, self - advance_paid)._compute_payment_state()
