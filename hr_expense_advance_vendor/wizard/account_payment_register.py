# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_product_advance(self):
        context = dict(self._context or {})
        active_ids = context.get("active_ids", [])
        move_ids = self.env["account.move"].browse(active_ids)
        expense_sheet = move_ids.line_ids.expense_id.sheet_id
        if expense_sheet.advance and expense_sheet.payment_mode == "company_account":
            return self.env.ref("hr_expense_advance_vendor.product_vendor_advance")
        return super()._get_product_advance()
