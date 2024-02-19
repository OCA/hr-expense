# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.onchange("product_id", "date", "account_id")
    def _onchange_product_id_date_account_id(self):
        """Set a specific context with the employee of the expense."""
        self = self.with_context(hr_expense_employee_id=self.employee_id.id)
        return super()._onchange_product_id_date_account_id()

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        """If the employee is changed, change the account by calling the existing
        onchange and emptying the existing data."""
        self.analytic_account_id = False
        self.analytic_tag_ids = [(5, 0)]
        self._onchange_product_id_date_account_id()
