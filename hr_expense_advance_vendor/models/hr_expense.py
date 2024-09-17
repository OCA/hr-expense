# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.constrains("advance")
    def _check_advance(self):
        vendor_advance = self.env.ref(
            "hr_expense_advance_vendor.product_vendor_advance"
        )
        for expense in self.filtered("advance"):
            if expense.product_id != vendor_advance:
                super(HrExpense, expense)._check_advance()
                continue
            if not vendor_advance.property_account_expense_id:
                raise ValidationError(
                    _("Vendor advance product has no payable account")
                )
            if expense.account_id != vendor_advance.property_account_expense_id:
                raise ValidationError(
                    _("Vendor advance, account must be the same payable account")
                )
            if expense.tax_ids:
                raise ValidationError(_("Vendor advance, all taxes must be removed"))
            if expense.payment_mode != "company_account":
                raise ValidationError(_("Vendor advance, paid by must be company"))
        return True

    def _get_product_advance(self):
        if self.advance and self.payment_mode == "company_account":
            return self.env.ref("hr_expense_advance_vendor.product_vendor_advance")
        return super()._get_product_advance()

    @api.onchange("advance", "payment_mode")
    def onchange_advance(self):
        if self.advance and self.payment_mode == "company_account":
            self.product_id = self.env.ref(
                "hr_expense_advance_vendor.product_vendor_advance"
            )
        else:
            return super().onchange_advance()
