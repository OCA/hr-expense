# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpenseAnalyticDistribution(models.Model):
    _name = "hr.expense.analytic.distribution"
    _description = "Shows the distribution of expenses."

    percentage = fields.Float("Percentage", required=True)
    analytic_account_id = fields.Many2one(
        "account.analytic.account",
        string="Analytic Account",
        required=True,
    )
    expense_id = fields.Many2one("hr.expense.sheet", string="Expense")
