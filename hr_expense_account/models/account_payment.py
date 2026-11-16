# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models

from . import hr_expense


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        """Skip posting when called from the expense draft bill workflow."""
        if self.env.context.get(hr_expense._EXPENSE_DRAFT_BILL_CTX):
            return
        return super().action_post()
