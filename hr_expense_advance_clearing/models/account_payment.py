# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_id = fields.Many2one(
        comodel_name="hr.expense",
        readonly=True,
    )

    @api.model
    def _get_valid_payment_account_types(self):
        account_types = super()._get_valid_payment_account_types()
        account_advance = self.env["account.account"].browse(
            self.env.context.get("hr_return_advance_account_id")
        )
        if (
            self.env.context.get("hr_return_advance")
            and account_advance.exists()
            and account_advance.account_type not in account_types
        ):
            account_types = [*account_types, account_advance.account_type]
        return account_types
