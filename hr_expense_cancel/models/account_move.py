# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_cancel(self):
        """Instead of refuse state on expense sheet,
        return state to your configuration."""
        res = super().button_cancel()
        cancel_state = (
            self.payment_id
            and self.env.company.expense_payment_cancel
            or self.env.company.expense_move_cancel
        )
        # Nothing to do, if you config refuse state
        if cancel_state == "cancel":
            return res
        for exp in self.line_ids.mapped("expense_id"):
            exp.write({"is_refused": False})
            exp.sheet_id.write({"state": cancel_state})
        return res
