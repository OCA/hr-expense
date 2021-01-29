# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpenseSheetInherit(models.Model):
    _inherit = "hr.expense.sheet"

    expense_distribution_ids = fields.One2many(
        "hr.expense.analytic.distribution", "expense_id", string="Distribution Lines"
    )
    count_percent = fields.Float(compute="_compute_count_percent")

    @api.depends("expense_distribution_ids.percentage")
    def _compute_count_percent(self):
        percent = 0.0
        for rec in self:
            for line in rec.expense_distribution_ids:
                percent += line.percentage
                if percent > 100:
                    raise UserError(_("Sorry, Percentage should be equal to 100."))
            rec.count_percent = 100 - percent
