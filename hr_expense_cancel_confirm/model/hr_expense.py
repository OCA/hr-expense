# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _name = "hr.expense.sheet"
    _inherit = ["hr.expense.sheet", "base.cancel.confirm"]

    _has_cancel_reason = "optional"  # ["no", "optional", "required"]

    def action_unpost(self):
        if not self.filtered("cancel_confirm"):
            return self.open_cancel_confirm_wizard()
        return super().action_unpost()

    def action_sheet_move_create(self):
        """Clear reason cancel when post journal entries on expense"""
        if not self._cancel_confirm_disabled():
            self.clear_cancel_confirm_data()
        return super().action_sheet_move_create()
