# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def remove_reconcile_expense_move(self):
        """The status of the expense will be reversed following configuration."""
        for move in self:
            cancel_state = (
                move.payment_id
                and move.env.company.expense_payment_cancel
                or move.env.company.expense_move_cancel
            )
            sheets = move.line_ids.mapped("expense_id.sheet_id")
            for sheet in sheets:
                # Clear account move, if you config refuse state
                if cancel_state == "cancel":
                    sheet.write({"account_move_id": False})
                    # Refuse flow with a similar employee who is paid by company
                    if sheet.payment_mode == "company_account":
                        sheet.expense_line_ids.refuse_expense(
                            reason=_("Payment Cancelled")
                        )
                else:  # Reversed status
                    sheet.expense_line_ids.write({"is_refused": False})
                    sheet.write({"state": cancel_state})

    def button_draft(self):
        self.remove_reconcile_expense_move()
        return super().button_draft()

    def button_cancel(self):
        self.remove_reconcile_expense_move()
        return super().button_cancel()

    def _reverse_moves(self, default_values_list=None, cancel=False):
        self.remove_reconcile_expense_move()
        return super()._reverse_moves(
            default_values_list=default_values_list, cancel=cancel
        )
