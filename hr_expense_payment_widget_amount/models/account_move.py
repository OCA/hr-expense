# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def js_remove_outstanding_partial(self, partial_id):
        """Expense Report can partial reconcile with multi line.
        So, this function will check all partial reconcile for multi unreconciled partial"""
        self.ensure_one()
        if self.payment_id.expense_sheet_ids:
            partial = self.env["account.partial.reconcile"].search(
                [("debit_move_id", "in", self.line_ids.ids)]
            )
            partial_id = len(partial) > 1 and partial.ids or partial_id
        res = super().js_remove_outstanding_partial(partial_id)
        # Back state to posted (if paid)
        self.payment_id.expense_sheet_ids.write({"state": "post"})
        return res
