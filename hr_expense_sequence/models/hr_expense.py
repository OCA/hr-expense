# Copyright 2025 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _prepare_payments_vals(self):
        """Use the expense report number as reference of the payment entries.

        Expenses paid by the company generate one journal entry (and its
        payment) per expense line, so the report number is the only value
        allowing to trace them back to the expense report when reconciling.
        """
        move_vals, payment_vals = super()._prepare_payments_vals()
        number = self.sheet_id.number
        if number and number != "/":
            move_vals["ref"] = number
            # `account.payment.memo` has an inverse writing back on
            # `account.move.ref`, and the payment is created right after the
            # move, so the memo has to be set as well to not lose the number.
            payment_vals["memo"] = number
        return move_vals, payment_vals
