# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_id = fields.Many2one(
        comodel_name="hr.expense",
        domain="[('expense_type', '=', 'advance')]",
        readonly=True,
        help="The employee advance this payment relates to — the advance it "
        "pays out, or the advance whose unused balance it returns.",
    )

    def _synchronize_from_moves(self, changed_fields):
        """Skip the standard move-payment sync for return-advance payments
        — the move is a generic entry, not the payment's own posting flow."""
        self = (
            self.with_context(skip_account_move_synchronization=True)
            if self.filtered("advance_id")
            else self
        )
        return super()._synchronize_from_moves(changed_fields)

    def action_post(self):
        """Reconcile the clearing entry against the payment that settles it."""
        res = super().action_post()
        for payment in self.filtered("move_id"):
            clearing_moves = payment.invoice_ids.filtered(
                lambda move: move.state == "posted"
                and move.move_type == "entry"
                and move.line_ids.expense_id.filtered("clearing_advance_id")
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
