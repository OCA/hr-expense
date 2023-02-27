# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class CancelConfirm(models.TransientModel):
    _inherit = "cancel.confirm"

    def confirm_cancel(self):
        res_model = self._context.get("cancel_res_model")
        res_ids = self._context.get("cancel_res_ids")
        if res_model == "hr.expense.sheet":
            docs = self.env[res_model].browse(res_ids)
            moves = docs.mapped("account_move_id")
            # Reason cancel move is equal expense, if install module account_move_cancel_confirm
            if hasattr(moves, "cancel_confirm"):
                moves.write(
                    {
                        "cancel_confirm": True,
                        "cancel_reason": self.cancel_reason,
                    }
                )
        return super().confirm_cancel()
