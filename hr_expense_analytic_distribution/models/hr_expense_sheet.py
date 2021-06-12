# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpenseSheetInherit(models.Model):
    _inherit = "hr.expense.sheet"

    expense_distribution_ids = fields.One2many(
        "hr.expense.analytic.distribution", "expense_id", string="Distribution Lines"
    )

    @api.constrains("expense_distribution_ids")
    def _constrains_distribution_ids_percentage(self):
        for report in self.filtered("expense_distribution_ids"):
            total_percent = sum(report.expense_distribution_ids.mapped("percentage"))
            if total_percent != 100:
                raise UserError(_("Sorry, Percentage should be equal to 100."))
