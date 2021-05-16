# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model
    def create(self, vals):
        if vals.get("advance") or self.env.context.get("default_advance"):
            number = self.env["ir.sequence"].next_by_code("hr.expense.sheet.advance")
            vals["number"] = number
        return super().create(vals)
