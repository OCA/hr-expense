# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _get_product_advance(self):
        if any(rec.advance and rec.payment_mode == "company_account" for rec in self):
            return self.env.ref("hr_expense_advance_vendor.product_vendor_advance")
        return super()._get_product_advance()

    def _update_sheets_pay_to_vendor(self):
        """No change state to post if document is clearing"""
        clearing_pay_to_vendor = self.filtered(lambda l: l.advance_sheet_id)
        if clearing_pay_to_vendor:
            self = self.with_context(skip_check_clearing_amount=1)
        clearing_less_advance = clearing_pay_to_vendor.filtered(
            lambda l: not l.amount_residual
        )
        # clearing less than advance, do not update state to post
        if clearing_less_advance:
            return
        return super()._update_sheets_pay_to_vendor()

    @api.constrains("state")
    def _check_constraint_clearing_amount(self):
        if not self.env.context.get("skip_check_clearing_amount", False):
            return super()._check_constraint_clearing_amount()

    def action_submit_sheet(self):
        """Check clearing has value 'Paid By' or 'To Vendor' is not same as advance"""
        for rec in self:
            advance = rec.advance_sheet_id
            if advance and (
                rec.payment_mode != advance.payment_mode
                or rec.vendor_id != advance.vendor_id
            ):
                raise UserError(
                    _(
                        "You cannot create a clearing document when 'Paid By' "
                        "or 'To Vendor' are not the same as the advance."
                    )
                )
        return super().action_submit_sheet()
