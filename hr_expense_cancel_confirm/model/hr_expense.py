# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _name = "hr.expense.sheet"
    _inherit = ["hr.expense.sheet", "base.cancel.confirm"]

    _has_cancel_reason = "optional"  # ["no", "optional", "required"]

    def action_cancel(self):
        if not self.filtered("cancel_confirm"):
            return self.open_cancel_confirm_wizard()
        return super().action_cancel()

    def action_sheet_move_create(self):
        self.clear_cancel_confirm_data()
        return super().action_sheet_move_create()

    def _cancel_account_move_document(self, moves):
        # Support cancel flow with module `account_move_cancel_confirm`
        if "cancel_confirm" in list(moves._fields.keys()) and self._context.get(
            "cancel_method"
        ):
            moves.button_draft()
            moves.write(
                {
                    "cancel_confirm": True,
                    "cancel_reason": self.cancel_reason,
                }
            )
            moves.button_cancel()
            return
        return super()._cancel_account_move_document()
