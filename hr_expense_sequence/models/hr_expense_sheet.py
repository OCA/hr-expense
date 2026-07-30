# Copyright 2014 Serv. Tecnol. Avanzados (http://www.serviciosbaeza.com)
#                       Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"
    _rec_name = "number"

    number = fields.Char(required=True, default="/", readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("number", "/") == "/":
                number = self.env["ir.sequence"].next_by_code("hr.expense.sheet") or "/"
                vals["number"] = number
        return super().create(vals_list)

    def _prepare_bills_vals(self):
        """Use the expense report number as reference of the vendor bill.

        `account.move.line.ref` is a stored related field on `account.move.ref`,
        so the number becomes available on every journal item, which allows
        reconciling the payable account by expense report number.
        """
        vals = super()._prepare_bills_vals()
        if self.number and self.number != "/":
            vals["ref"] = self.number
            # Sets the label of the payable journal item to the number as well.
            vals["payment_reference"] = self.number
        return vals
