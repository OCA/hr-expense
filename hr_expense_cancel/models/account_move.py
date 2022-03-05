# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_cancel(self):
        """Instead of refuse state on expense sheet,
        return state to your configuration."""
        res = super().button_cancel()
        cancel_state = (
            self.payment_id
            and self.env.company.expense_payment_cancel
            or self.env.company.expense_move_cancel
        )
        expense_sheet_ids = self.env.context.get("expense_sheet_ids", [])
        sheets = self.env["hr.expense.sheet"].browse(expense_sheet_ids)
        for sheet in sheets:
            # Clear account move, if you config refuse state
            if cancel_state == "cancel":
                sheet.write({"account_move_id": False})
                # Refuse flow with a similar employee who is paid by company
                if sheet.payment_mode == "company_account":
                    sheet.expense_line_ids.refuse_expense(reason=_("Payment Cancelled"))
            else:
                sheet.expense_line_ids.write({"is_refused": False})
                sheet.write({"state": cancel_state})
        return res
