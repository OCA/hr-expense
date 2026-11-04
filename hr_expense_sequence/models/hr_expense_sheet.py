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

    def _prefix_with_number(self, reference):
        """Prepend the expense report number to ``reference``.

        The number is a prefix rather than a replacement so the reference the
        accounting documents used to carry is not lost, and so sorting journal
        items by reference groups them by expense report.
        """
        self.ensure_one()
        if not self.number or self.number == "/":
            return reference
        if not reference:
            return self.number
        return f"{self.number} - {reference}"

    def _prepare_bills_vals(self):
        """Prefix the vendor bill reference with the expense report number.

        `account.move.line.ref` is a stored related field on `account.move.ref`,
        so the number becomes available on every journal item, which allows
        reconciling the payable account by expense report number.
        """
        vals = super()._prepare_bills_vals()
        reference = self._prefix_with_number(vals.get("ref"))
        vals["ref"] = reference
        # Labels the payable journal item. Core builds that label out of both
        # fields and concatenates them when they differ, so they are kept equal.
        vals["payment_reference"] = reference
        return vals
