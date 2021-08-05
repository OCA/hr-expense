# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def create(self, vals):
        expense_line = vals.get("expense_line_ids", False)
        from_expense = expense_line and expense_line[0][2] or False
        number = vals.get("number", "/")
        if number == "/" and from_expense:
            # For case: expense created by widget one2many
            if expense_line[0][0] == 0:
                if any(exp[2]["advance"] for exp in expense_line):
                    number = self.env["ir.sequence"].next_by_code(
                        "hr.expense.sheet.advance"
                    )
            else:
                expenses = self.env["hr.expense"].browse(from_expense)
                if any(exp.advance for exp in expenses):
                    number = self.env["ir.sequence"].next_by_code(
                        "hr.expense.sheet.advance"
                    )
            vals["number"] = number
        return super().create(vals)
