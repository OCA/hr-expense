# Copyright 2025 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _prepare_payments_vals(self):
        """Prefix the payment entries reference with the expense report number.

        Expenses paid by the company generate one journal entry (and its
        payment) per expense line: the number ties them back to the expense
        report when reconciling, while the reference they already carried keeps
        them apart from each other.
        """
        move_vals, payment_vals = super()._prepare_payments_vals()
        reference = self.sheet_id._prefix_with_number(move_vals.get("ref"))
        move_vals["ref"] = reference
        # `account.payment.memo` has an inverse writing back on
        # `account.move.ref`, and the payment is created right after the move,
        # so the memo has to be set as well to not lose the number.
        payment_vals["memo"] = reference
        return move_vals, payment_vals
