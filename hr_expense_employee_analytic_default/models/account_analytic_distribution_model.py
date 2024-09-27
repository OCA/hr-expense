# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountAnalyticDistributionModel(models.Model):
    _inherit = "account.analytic.distribution.model"

    @api.model
    def _get_distribution(self, vals):
        """If custom context is set, change partner to user partner of the employee
        to get the correct distribution."""
        if self.env.context.get("hr_expense_employee_id"):
            employee = self.env["hr.employee"].browse(
                self.env.context.get("hr_expense_employee_id")
            )
            if employee.address_id:
                vals.update(partner_id=employee.address_id.id)
        return super()._get_distribution(vals)
