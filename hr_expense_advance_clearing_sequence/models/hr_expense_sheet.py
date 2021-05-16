# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def create(self, vals):
        from_expense = (
            vals.get("expense_line_ids", False)
            and vals["expense_line_ids"][0][2]
            or False
        )
        if vals.get("number", "/") == "/" and from_expense:
            expenses = self.env["hr.expense"].browse(from_expense)
            if any(exp.advance for exp in expenses):
                number = self.env["ir.sequence"].next_by_code(
                    "hr.expense.sheet.advance"
                )
                vals["number"] = number
        return super().create(vals)
