# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def button_draft(self):
        return super(
            AccountMove, self.with_context(skip_move_refresh=True)
        ).button_draft()

    def button_cancel(self):
        return super(
            AccountMove, self.with_context(skip_move_refresh=True)
        ).button_cancel()
