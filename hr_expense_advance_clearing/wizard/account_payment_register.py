# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from werkzeug.urls import url_encode

from odoo import _, api, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model
    def default_get(self, fields_list):
        """Step to avoid UserError from core odoo:
        - Change account type to receivable
        - Call super() and rollback account to origin
        """
        advance_return = self._context.get("hr_return_advance", False)
        origin_account = False
        if advance_return and self._context.get("active_model") == "account.move":
            lines = (
                self.env["account.move"]
                .browse(self._context.get("active_ids", []))
                .line_ids
            )
            line = lines.filtered(
                lambda l: l.expense_id.advance and not l.full_reconcile_id
            )
            if line and line.account_internal_type not in ("receivable", "payable"):
                origin_account = [
                    line.account_internal_type,
                    line.account_id.internal_type,
                ]
                line.account_internal_type = "receivable"
                line.account_id.internal_type = "receivable"
        res = super().default_get(fields_list)
        if origin_account:
            line.account_internal_type = origin_account[0]
            line.account_id.internal_type = origin_account[1]
        return res

    def action_create_payments(self):
        if self._context.get("hr_return_advance", False):
            return self.expense_post_return_advance()
        return super().action_create_payments()

    def expense_post_return_advance(self):
        """This is opposite operation of action_create_payments(),
        it return remaining advance from employee back to company
        """
        self.ensure_one()
        context = dict(self._context or {})
        active_ids = context.get("active_ids", [])
        move_ids = self.env["account.move"].browse(active_ids)
        ctx = {"skip_account_move_synchronization": True}
        expense_sheet = move_ids.line_ids.expense_id.sheet_id
        emp_advance = self.env.ref("hr_expense_advance_clearing.product_emp_advance")
        advance_account = emp_advance.property_account_expense_id
        # Create return advance and post it
        payment_vals = self._create_payment_vals_from_wizard()
        payment_vals_list = [payment_vals]
        payment = (
            self.env["account.payment"].with_context(ctx).create(payment_vals_list)
        )
        # Set new payment_type and payment entry to be Dr Bank, Cr Advance
        payment.write(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "destination_account_id": advance_account,
            }
        )
        payment.action_post()

        # Log the return advance in the chatter
        body = _(
            "A remaining advance return of %s %s with the reference "
            "<a href='/mail/view?%s'>%s</a> related to your expense %s "
            "has been made."
        ) % (
            payment.amount,
            payment.currency_id.symbol,
            url_encode({"model": "account.payment", "res_id": payment.id}),
            payment.name,
            expense_sheet.name,
        )
        expense_sheet.message_post(body=body)

        # Reconcile the return advance and the advance,
        # i.e. lookup on the advance account on move lines
        account_move_lines_to_reconcile = self.env["account.move.line"]
        for line in payment.move_id.line_ids + expense_sheet.account_move_id.line_ids:
            if line.account_id == advance_account:
                account_move_lines_to_reconcile |= line
        account_move_lines_to_reconcile.with_context(ctx).reconcile()
        return {"type": "ir.actions.act_window_close"}
