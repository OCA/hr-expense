# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def remove_move_reconcile(self):
        res = super().remove_move_reconcile()
        payments = self.env["account.payment"].search(
            [("move_id", "in", self.mapped("move_id").ids)]
        )
        for payment in payments:
            if payment.payment_type == "outbound":
                expense_sheets = payments.mapped("expense_sheet_ids")
                expense_sheets.write({"state": "post"})
        return res
