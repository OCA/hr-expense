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

    def action_post(self):
        res = super().action_post()
        for payment in self.filtered("move_id"):
            clearing_moves = payment.invoice_ids.filtered(
                lambda move: move.state == "posted"
                and move.move_type == "entry"
                and move.expense_sheet_id.advance_sheet_id
            )
            if not clearing_moves:
                continue

            lines = (clearing_moves + payment.move_id).line_ids.filtered(
                lambda line: line.account_id.reconcile
                and not line.reconciled
                and line.account_id.account_type
                in ("asset_receivable", "liability_payable")
            )
            for account in lines.account_id:
                account_lines = lines.filtered_domain([("account_id", "=", account.id)])
                if len(account_lines) > 1:
                    account_lines.reconcile()
        return res

    @api.model
    def _get_valid_payment_account_types(self):
        account_types = super()._get_valid_payment_account_types()
        if self.env.context.get("hr_return_advance"):
            account_types.append("asset_current")
        return account_types
