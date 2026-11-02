# Copyright 2019 Ecosoft <saranl@ecosoft.co.th>
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2024 Tecnativa - Pedro M. Baeza
# Copyright 2026 Moduon - Eduardo de Miguel
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    invoice_expense_ids = fields.One2many(
        comodel_name="hr.expense", inverse_name="invoice_id", string="Expenses"
    )
    source_invoice_expense_id = fields.Many2one(
        comodel_name="hr.expense",
        help="Reference to the expense with a linked invoice that generated this"
        "transfer journal entry",
    )

    @api.constrains("amount_total")
    def _check_expense_ids(self):
        DecimalPrecision = self.env["decimal.precision"]
        precision = DecimalPrecision.precision_get("Product Price")
        for move in self.filtered("invoice_expense_ids"):
            expense_amount = sum(
                move.invoice_expense_ids.mapped("total_amount_currency")
            )
            if float_compare(expense_amount, move.amount_total, precision) != 0:
                raise ValidationError(
                    self.env._(
                        "You can't change the total amount, as there's an expense "
                        "linked to this invoice."
                    )
                )

    def action_force_register_payment(self):
        if self.source_invoice_expense_id:
            return self.line_ids.action_register_payment()
        return super().action_force_register_payment()

    def _compute_nb_expenses(self):
        res = super()._compute_nb_expenses()
        for move in self.filtered("invoice_expense_ids"):
            move.nb_expenses = len(move.invoice_expense_ids)
        return res

    def action_open_expense(self):
        self.ensure_one()
        if not self.invoice_expense_ids:
            return super().action_open_expense()
        return self.invoice_expense_ids._get_records_action()
