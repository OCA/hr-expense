# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def remove_move_reconcile(self):
        res = super().remove_move_reconcile()
        payment = self.env["account.payment"].search(
            [("move_id", "=", self.move_id.id)]
        )
        if payment:
            expense_sheet = payment.expense_sheet_ids
            expense_sheet.write({"state": "post"})
        return res
