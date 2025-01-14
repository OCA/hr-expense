# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)


from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _validate_over_return(self):
        """Actual remaining = amount to clear - clear pending
        and it is not legit to return more than remaining"""
        clearings = (
            self.env["hr.expense.sheet"]
            .browse(self.env.context.get("clearing_sheet_ids", []))
            .filtered(lambda sheet: sheet.state == "approve")
        )
        amount_not_clear = sum(clearings.mapped("total_amount"))
        actual_remaining = self.source_amount_currency - amount_not_clear
        more_info = ""
        symbol = self.source_currency_id.symbol
        if amount_not_clear:
            more_info = _("\nNote: pending amount clearing is %(symbol)s%(amount)s") % {
                "symbol": symbol,
                "amount": f"{amount_not_clear:,.2f}",
            }
        if float_compare(self.amount, actual_remaining, 2) == 1:
            raise UserError(
                _(
                    "You cannot return advance more than actual remaining "
                    "(%(symbol)s%(amount)s)%(more_info)s"
                )
                % {
                    "symbol": symbol,
                    "amount": f"{actual_remaining:,.2f}",
                    "more_info": more_info,
                }
            )

    def _init_payments(self, to_process, edit_mode=False):
        if self.env.context.get("hr_return_advance"):
            self._validate_over_return()
            active_ids = self.env.context.get("active_ids", [])
            if self.env.context.get("active_model") == "account.move":
                lines = self.env["account.move"].browse(active_ids).line_ids
            elif self.env.context.get("active_model") == "account.move.line":
                lines = self.env["account.move.line"].browse(active_ids)

            expense_sheet = lines.expense_id.sheet_id
            for x in to_process:
                x["create_vals"]["partner_type"] = "customer"
                x["create_vals"]["advance_id"] = expense_sheet.id

        payments = super()._init_payments(to_process, edit_mode)
        return payments

    def _create_payments(self):
        """Update the payment state when the clearing amount exceeds the advance."""
        payments = super()._create_payments()
        if self.env.context.get("expense_clearing"):
            for payment in payments:
                payment.write({"move_id": payment.move_id.id, "state": "paid"})
        return payments
