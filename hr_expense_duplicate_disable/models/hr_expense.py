# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, models
from odoo.tools import str2bool


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.depends("employee_id", "product_id", "total_amount_currency")
    def _compute_duplicate_expense_ids(self):
        if not str2bool(
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hr_expense_disable_duplicate_detection", "False")
        ):
            return super()._compute_duplicate_expense_ids()
        self.duplicate_expense_ids = [Command.clear()]
