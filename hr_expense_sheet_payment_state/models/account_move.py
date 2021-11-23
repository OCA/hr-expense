# Copyright 2021 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def is_invoice(self, include_receipts=False):
        # Override move type check in the context of hr.expense.sheet payment_state computation,
        # because the move linked to an expense sheet is of type entry.
        self.ensure_one()
        if self.env.context.get("payment_state_matters") and self.line_ids.expense_id:
            return True
        return super().is_invoice(include_receipts)

    def _compute_amount(self):
        # add key in the context of hr.expense.sheet payment_state computation
        self = self.with_context(payment_state_matters=True)
        return super()._compute_amount()
