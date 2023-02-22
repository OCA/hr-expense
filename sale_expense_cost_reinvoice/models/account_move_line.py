# Copyright 2022 Camptocamp SA (https://www.camptocamp.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _sale_prepare_sale_line_values(self, order, price):
        # when reinvocing at cost (expense product invoice policy is set to "At cost")
        # the sale order line cost (purchase_price) is the actual expense cost
        self.ensure_one()
        sale_line_values = super()._sale_prepare_sale_line_values(order, price)
        if self.expense_id and self.expense_id.product_id.expense_policy == "cost":
            sale_line_values.update({"purchase_price": price})
        return sale_line_values
