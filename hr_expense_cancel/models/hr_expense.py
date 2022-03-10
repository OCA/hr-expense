# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_cancel(self):
        move_cancel_state = self.env.company.expense_move_cancel
        # Cancel following standard odoo (posted -> draft -> cancel)
        for sheet in self:
            sheet.account_move_id.button_draft()  # unreconciled move line
            sheet.account_move_id.button_cancel()
        # Reset is_refused on expense, if not cancel
        if move_cancel_state != "cancel":
            self.mapped("expense_line_ids").write({"is_refused": False})
        return self.write({"state": move_cancel_state, "account_move_id": False})
