# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def create(self, vals):
        if "expense_line_ids" in vals.keys():
            from_expense = vals["expense_line_ids"][0][2]
            expense = self.env["hr.expense"].browse(from_expense)
            if vals.get("number", "/") == "/" and expense.advance:
                number = self.env["ir.sequence"].next_by_code(
                    "hr.expense.sheet.advance"
                )
                vals["number"] = number
        return super().create(vals)
