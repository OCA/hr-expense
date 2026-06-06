# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_sync_account_moves(self):
        """manually regenerate draft account moves
        to sync with the current expense line data."""
        return self._refresh_account_moves()

    def _refresh_account_moves(self):
        """Delete draft account moves (and linked payments) then recreate
        them to sync with the current expense line data.

        This is called after expense fields that affect the move are
        modified while the sheet is in the 'approve' state.
        """
        sheets_to_recreate = self.env["hr.expense.sheet"]
        for sheet in self:
            draft_moves = sheet.sudo().account_move_ids.filtered(
                lambda m: m.state == "draft"
            )
            if not draft_moves:
                continue

            # Delete linked payments first (company_account flow)
            payments = draft_moves.origin_payment_id
            if payments:
                payments.sudo().unlink()
            else:
                draft_moves.sudo().unlink()
            sheets_to_recreate |= sheet
        if sheets_to_recreate:
            return sheets_to_recreate._do_create_moves()
        return False
