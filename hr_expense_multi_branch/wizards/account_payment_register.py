# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_reconciled_all_moves(self, payment):
        expenses = payment.move_id.line_ids.mapped("expense_id")
        return (
            expenses.mapped("sheet_id.account_move_id")
            if expenses
            else super()._get_reconciled_moves(payment)
        )
