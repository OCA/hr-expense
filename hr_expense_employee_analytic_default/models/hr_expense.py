# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.depends("employee_id")
    def _compute_analytic_distribution(self):
        """Set a specific context with the employee of the expense."""
        self = self.with_context(hr_expense_employee_id=self.employee_id.id)
        return super()._compute_analytic_distribution()
