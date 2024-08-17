# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.models import BaseModel
from odoo.tools import float_compare


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_default_advance(self, fields_list):
        """Call default_get from BaseModel"""
        defaults = BaseModel.default_get(self, fields_list)
        return defaults

    def _default_return_advance(self, fields_list):
        """OVERRIDE: lines without check account_internal_type for return advance only"""
        res = self._get_default_advance(fields_list)
        if "line_ids" in fields_list:
            lines = (
                self.env["account.move"]
                .browse(self._context.get("active_ids", []))
                .line_ids
            )

            # Keep lines having a residual amount to pay.
            available_lines = self.env["account.move.line"]
            for line in lines:
                if line.move_id.state != "posted":
                    raise UserError(
                        _("You can only register payment for posted journal entries.")
                    )
                if not line.product_id:
                    continue
                if line.currency_id:
                    if line.currency_id.is_zero(line.amount_residual_currency):
                        continue
                else:
                    if line.company_currency_id.is_zero(line.amount_residual):
                        continue
                available_lines |= line
            # Check.
            if not available_lines:
                raise UserError(
                    _(
                        "You can't register a payment because "
                        "there is nothing left to pay on the selected journal items."
                    )
                )
            if len(lines.company_id) > 1:
                raise UserError(
                    _(
                        "You can't create payments for entries belonging "
                        "to different companies."
                    )
                )
            res["line_ids"] = [(6, 0, available_lines.ids)]
        return res

    @api.model
    def default_get(self, fields_list):
        if self._context.get("hr_return_advance", False):
            return self._default_return_advance(fields_list)
        return super().default_get(fields_list)

    def _validate_over_return(self):
        """Actual remaining = amount to clear - clear pending
        and it is not legit to return more than remaining"""
        clearings = (
            self.env["hr.expense.sheet"]
            .browse(self.env.context.get("clearing_sheet_ids", []))
            .filtered(lambda l: l.state == "approve")
        )
        amount_not_clear = sum(clearings.mapped("total_amount"))
        actual_remaining = self.source_amount_currency - amount_not_clear
        more_info = ""
        symbol = self.source_currency_id.symbol
        if amount_not_clear:
            more_info = _("\nNote: pending amount clearing is %(symbol)s%(amount)s") % {
                "symbol": symbol,
                "amount": "{:,.2f}".format(amount_not_clear),
            }
        if float_compare(self.amount, actual_remaining, 2) == 1:
            raise UserError(
                _(
                    "You cannot return advance more than actual remaining "
                    "(%(symbol)s%(amount)s)%(more_info)s"
                )
                % {
                    "symbol": symbol,
                    "amount": "{:,.2f}".format(actual_remaining),
                    "more_info": more_info,
                }
            )

    def action_create_payments(self):
        if self._context.get("hr_return_advance", False):
            self._validate_over_return()
            self.expense_post_return_advance()
            return {"type": "ir.actions.act_window_close"}
        return super().action_create_payments()

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        if self._context.get("hr_return_advance", False):
            # Add advance in payment return
            active_ids = self._context.get("active_ids", [])
            move_ids = self.env["account.move"].browse(active_ids)
            payment_vals["advance_id"] = move_ids.line_ids.expense_id.sheet_id.id
        return payment_vals

    def _create_payment_return_advance(self, ctx, advance_account):
        payment_vals = self._create_payment_vals_from_wizard()
        payment_vals_list = [payment_vals]
        payment = (
            self.env["account.payment"].with_context(**ctx).create(payment_vals_list)
        )
        # Set new payment_type and payment entry to be Dr Bank, Cr Advance
        payment.write(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "destination_account_id": advance_account,
            }
        )
        return payment

    def _get_product_advance(self):
        return self.env.ref("hr_expense_advance_clearing.product_emp_advance")

    def expense_post_return_advance(self):
        """This is opposite operation of action_create_payments(),
        it return remaining advance from employee back to company
        """
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get("active_ids", [])
        move_ids = self.env["account.move"].browse(active_ids)
        ctx = self._context.copy()
        ctx.update({"skip_account_move_synchronization": True})
        expense_sheet = move_ids.line_ids.expense_id.sheet_id
        emp_advance = self._get_product_advance()
        advance_account = emp_advance.property_account_expense_id
        # Create return advance and post it
        payment = self._create_payment_return_advance(ctx, advance_account)
        payment.action_post()

        redirect_link = (
            f"<a href=# data-oe-model=account.payment data-oe-id={payment.id}>"
            f"{payment.name}</a>"
        )  # Account Payment link
        # Log the return advance in the chatter
        body = _(
            "A remaining advance return of %(amount)s %(symbol)s with the reference "
            "%(ref)s related to your expense %(name)s has been made."
        ) % {
            "amount": payment.amount,
            "symbol": payment.currency_id.symbol,
            "ref": redirect_link,
            "name": expense_sheet.name,
        }
        expense_sheet.message_post(body=body)

        # Reconcile the return advance and the advance,
        # i.e. lookup on the advance account on move lines
        account_move_lines_to_reconcile = self.env["account.move.line"]
        for line in payment.move_id.line_ids + expense_sheet.account_move_id.line_ids:
            if line.account_id == advance_account and not line.reconciled:
                account_move_lines_to_reconcile |= line
        res = account_move_lines_to_reconcile.with_context(**ctx).reconcile()
        return res
