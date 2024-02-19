# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountAnalyticDefault(models.Model):
    _inherit = "account.analytic.default"

    @api.model
    def account_get(
        self,
        product_id=None,
        partner_id=None,
        account_id=None,
        user_id=None,
        date=None,
        company_id=None,
    ):
        """If custom context is set, change partner to user partner of the employee
        to get the correct value."""
        if self.env.context.get("hr_expense_employee_id"):
            employee = self.env["hr.employee"].browse(
                self.env.context.get("hr_expense_employee_id")
            )
            if employee.address_id:
                partner_id = employee.address_id.id
        return super().account_get(
            product_id=product_id,
            partner_id=partner_id,
            account_id=account_id,
            user_id=user_id,
            date=date,
            company_id=company_id,
        )
