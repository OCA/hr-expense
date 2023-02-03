# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _compute_purchase_price(self):
        # if expense product standard_price is 0 and expense_policy is cost
        # we don't want purchase_price on order line to be computed to 0
        # that is how standard odoo works
        # instead we will take expense price, from just created order line
        # with the values from _sale_prepare_sale_line_values
        at_cost_expense_lines = self.filtered(
            lambda line: line.is_expense and line.product_id.expense_policy == "cost"
        )
        at_cost_prices = {
            line.id: line.purchase_price for line in at_cost_expense_lines
        }
        super()._compute_purchase_price()
        for line in at_cost_expense_lines:
            line = line.with_company(line.company_id)
            product_cost = at_cost_prices.get(line.id)
            line.purchase_price = line._convert_price(
                product_cost, line.product_id.uom_id
            )
        return
