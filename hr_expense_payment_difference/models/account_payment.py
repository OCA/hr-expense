# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.depends("invoice_ids", "amount", "payment_date", "currency_id", "payment_type")
    def _compute_payment_difference(self):
        res = super()._compute_payment_difference()
        for payment in self.filtered(lambda p: p.state == "draft"):
            context = dict(self._context or {})
            if context.get("active_model", False) == "hr.expense.sheet" and context.get(
                "default_amount", False
            ):
                active_id = context.get("active_id", False)
                expense_sheet = self.env["hr.expense.sheet"].browse(active_id)
                payment.payment_difference = (
                    context.get("default_amount") - expense_sheet.difference_residual
                )
        return res
