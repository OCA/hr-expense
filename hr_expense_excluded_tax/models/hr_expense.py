# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    # Overwrite domain tax_ids without price_include = True
    tax_ids = fields.Many2many(
        domain="[('company_id', '=', company_id), ('type_tax_use', '=', 'purchase')]",
    )

    @api.depends("total_amount", "tax_ids", "currency_id")
    def _compute_amount_tax(self):
        """Calculate untaxed_amount if the user selects
        excluded tax in a product that has a cost"""
        res = super()._compute_amount_tax()
        for expense in self:
            if expense.product_has_cost:
                taxes = expense.tax_ids.compute_all(
                    expense.unit_amount,
                    expense.currency_id,
                    expense.quantity,
                    expense.product_id,
                    expense.employee_id.user_id.partner_id,
                )
                expense.untaxed_amount = taxes.get("total_excluded")
        return res
