# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    @api.model
    def _get_line_batch_key(self, line):
        batch_key = super()._get_line_batch_key(line)
        if self.env.context.get("hr_return_advance"):
            batch_key["partner_type"] = "customer"
        return batch_key

    def _init_payments(self, to_process, edit_mode=False):
        if self.env.context.get("hr_return_advance"):
            advance = self.env["hr.expense"].browse(
                self.env.context.get("hr_return_advance_id")
            )
            if not advance.exists():
                raise UserError(self.env._("No employee advance was found to return."))
            for payment_vals in to_process:
                payment_vals["create_vals"]["advance_id"] = advance.id
        return super()._init_payments(to_process, edit_mode=edit_mode)

    def _create_payments(self):
        if self.env.context.get("hr_return_advance"):
            self.ensure_one()
            maximum_amount = self._get_total_amounts_to_pay(self.batches)["full_amount"]
            if self.currency_id.compare_amounts(self.amount, maximum_amount) > 0:
                raise UserError(
                    self.env._(
                        "You cannot return more than "
                        "the remaining advance (%(amount)s).",
                        amount=format_amount(
                            self.env,
                            maximum_amount,
                            self.currency_id,
                        ),
                    )
                )
        return super()._create_payments()
