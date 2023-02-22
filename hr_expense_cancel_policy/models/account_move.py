# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_cancel(self):
        """Instead of refuse state on expense sheet,
        return state to your configuration."""
        cancel_state = (
            self.env.company.payment_cancel_policy
            if self.payment_id
            else self.env.company.je_cancel_policy
        )
        skip_refuse = cancel_state != "cancel"
        res = super(
            AccountMove, self.with_context(skip_refuse_expense=skip_refuse)
        ).button_cancel()
        if skip_refuse:
            expenses = self.line_ids.mapped("expense_id")
            sheets = expenses.mapped("sheet_id")
            sheets.write({"state": cancel_state})
        return res
