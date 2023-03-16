# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.depends("employee_id", "product_id", "total_amount")
    def _compute_duplicate_expense_ids(self):
        if not self.env.company.disable_confirm_expense_duplicate:
            return super()._compute_duplicate_expense_ids()
        for rec in self:
            rec.duplicate_expense_ids = [(5, 0, 0)]
