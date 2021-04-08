# Copyright 2019 Ecosoft <saranl@ecosoft.co.th>
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_ids = fields.One2many(
        comodel_name="hr.expense", inverse_name="invoice_id", string="Expenses"
    )

    @api.constrains("amount_total")
    def _check_expense_ids(self):
        for move in self.filtered("expense_ids"):
            DecimalPrecision = self.env["decimal.precision"]
            precision = DecimalPrecision.precision_get("Product Price")
            expense_amount = sum(move.expense_ids.mapped("total_amount"))
            if float_compare(expense_amount, move.amount_total, precision) != 0:
                raise ValidationError(
                    _(
                        "You can't change the total amount, as there's an expense "
                        "linked to this invoice."
                    )
                )

    def _get_cash_basis_matched_percentage(self):
        res = super()._get_cash_basis_matched_percentage()
        if (
            res == 1
            and self._context.get("use_hr_expense_invoice")
            and self._context.get("default_expense_line_ids")
        ):
            return False
        return res
