# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _is_auto_refresh(self):
        return self.env.company.auto_refresh_account_moves

    def _domain_refresh(self, sheet):
        return sheet and sheet.state == "approve" and sheet.account_move_ids

    def write(self, vals):
        sheets_to_refresh = self.env["hr.expense.sheet"]
        # skip_move_refresh is set by account.move button_draft/button_cancel:
        # when a move is reset/cancelled, the writes triggered on its expense
        # lines are not user edits and must not regenerate the draft move.
        if self._is_auto_refresh() and not self.env.context.get("skip_move_refresh"):
            for expense in self:
                sheet = expense.sheet_id
                if expense._domain_refresh(sheet):
                    sheets_to_refresh |= sheet
        res = super().write(vals)
        if sheets_to_refresh:
            sheets_to_refresh._refresh_account_moves()
        return res
