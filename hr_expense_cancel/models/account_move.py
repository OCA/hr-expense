# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def remove_move_reconcile(self):
        """Remove the relationship between expenses and payments
        after removing the reconciliation."""
        res = super().remove_move_reconcile()
        moves = self.mapped("move_id")
        sheets = self.mapped("expense_id.sheet_id")
        for move in moves:
            cancel_state = (
                move.payment_id
                and move.env.company.expense_payment_cancel
                or move.env.company.expense_move_cancel
            )
            for sheet in sheets:
                # Clear account move, if you config refuse state
                if cancel_state == "cancel":
                    sheet.write({"account_move_id": False})
                    # Refuse flow with a similar employee who is paid by company
                    if sheet.payment_mode == "company_account":
                        sheet.expense_line_ids.refuse_expense(
                            reason=_("Payment Cancelled")
                        )
                else:  # Back state
                    sheet.expense_line_ids.write({"is_refused": False})
                    sheet.write({"state": cancel_state})
        return res
