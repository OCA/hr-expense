# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_product_advance(self):
        return self.env.ref("hr_expense_advance_clearing.product_emp_advance", False)

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

    def action_create_payments(self):
        if self._context.get("hr_return_advance", False):
            self._validate_over_return()
            self.expense_post_return_advance()
            return {"type": "ir.actions.act_window_close"}
        return super().action_create_payments()

    def expense_post_return_advance(self):
        """This is opposite operation of action_create_payments(),
        it return remaining advance from employee back to company
        """
        self.ensure_one()
        ctx = self._context.copy()
        ctx.update({"skip_account_move_synchronization": True})

        if self._context.get("active_model") == "account.move":
            lines = (
                self.env["account.move"]
                .browse(self._context.get("active_ids", []))
                .line_ids
            )
        elif self._context.get("active_model") == "account.move.line":
            lines = self.env["account.move.line"].browse(
                self._context.get("active_ids", [])
            )

        expense_sheet = lines.expense_id.sheet_id
        emp_advance = self._get_product_advance()
        advance_account = emp_advance.property_account_expense_id
        # Create return advance and post it
        batches = self._get_batches()
        first_batch_result = batches[0]
        payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
        # Set new payment_type and payment entry to be Dr Bank, Cr Advance
        payment_vals["advance_id"] = expense_sheet.id
        payment_vals["partner_type"] = "customer"
        payment_vals["destination_account_id"] = advance_account.id
        payment_vals_list = [payment_vals]
        payment = (
            self.env["account.payment"].with_context(**ctx).create(payment_vals_list)
        )
        payment.action_post()

        # Log the return advance in the chatter
        body = _(
            "A remaining advance return of %(amount)s %(symbol)s with the reference "
            "%(ref)s related to your expense %(name)s has been made."
        ) % {
            "amount": payment.amount,
            "symbol": payment.currency_id.symbol,
            "ref": payment._get_html_link(),
            "name": expense_sheet.name,
        }
        expense_sheet.message_post(body=Markup(body))

        # Reconcile the return advance and the advance,
        # i.e. lookup on the advance account on move lines
        account_move_lines_to_reconcile = self.env["account.move.line"]
        for line in payment.move_id.line_ids + expense_sheet.account_move_ids.line_ids:
            if line.account_id == advance_account and not line.reconciled:
                account_move_lines_to_reconcile |= line
        res = account_move_lines_to_reconcile.with_context(**ctx).reconcile()
        return res
