# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        readonly=True,
    )

    def _synchronize_from_moves(self, changed_fields):
        """skip check when payment is return advance"""
        self = (
            self.with_context(skip_account_move_synchronization=True)
            if self.filtered("advance_id")
            else self
        )
        return super()._synchronize_from_moves(changed_fields)

    @api.model
    def _get_valid_payment_account_types(self):
        account_types = super()._get_valid_payment_account_types()
        if self.env.context.get("hr_return_advance"):
            account_types.append("asset_current")
        return account_types
