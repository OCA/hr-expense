# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_cancel(self):
        """ Send context expense sheet """
        return super(
            AccountPayment,
            self.with_context(expense_sheet_ids=self.expense_sheet_ids.ids),
        ).action_cancel()
