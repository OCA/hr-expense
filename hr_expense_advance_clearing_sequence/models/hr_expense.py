# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.model_create_multi
    def create(self, vals_list):
        default_type = self.env.context.get("default_expense_type")
        for vals in vals_list:
            expense_type = vals.get("expense_type", default_type)
            if expense_type == "advance" and vals.get("number", "/") == "/":
                vals["number"] = (
                    self.env["ir.sequence"].next_by_code("hr.expense.sheet.advance")
                    or "/"
                )
        return super().create(vals_list)
