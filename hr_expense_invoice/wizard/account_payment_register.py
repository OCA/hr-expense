# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import ValidationError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def action_create_payments(self):
        # Do not allow register payment for invoices from expenses
        expenses = (
            self.env["hr.expense"]
            .sudo()
            .search([("invoice_id", "in", self.line_ids.mapped("move_id").ids)])
        )
        if expenses:
            raise ValidationError(
                _("Register payment on expense's invoice is not allowed")
            )
        return super().action_create_payments()
