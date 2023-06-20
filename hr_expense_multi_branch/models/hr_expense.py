# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _prepare_move_values(self):
        move_values = super()._prepare_move_values()
        move_values["branch_id"] = self.sheet_id.branch_id
        return move_values
