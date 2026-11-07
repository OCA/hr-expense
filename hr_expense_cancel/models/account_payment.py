# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_draft_cancel(self):
        for payment in self:
            payment.action_draft()
            payment.action_cancel()
