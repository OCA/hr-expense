# Copyright 2019 Ecosoft <saranl@ecosoft.co.th>
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_ids = fields.One2many(
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
        for move in self.filtered("expense_ids"):
            expense_amount = sum(move.expense_ids.mapped("total_amount_currency"))
            if float_compare(expense_amount, move.amount_total, precision) != 0:
                raise ValidationError(
                    _(
                        "You can't change the total amount, as there's an expense "
                        "linked to this invoice."
                    )
                )

    def action_view_expense(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.expense",
            "res_id": self.expense_ids[:1].id,
        }


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains("account_id", "display_type")
    def _check_payable_receivable(self):
        _self = self.filtered("expense_id")
        return super(AccountMoveLine, (self - _self))._check_payable_receivable()

    def reconcile(self):
        """Mark expenses paid by employee having invoice when reconciling them."""
        expenses = self.move_id.source_invoice_expense_id
        not_paid_expenses = expenses.filtered(lambda x: x.state != "done")
        res = super().reconcile()
        not_paid_expense_sheets = not_paid_expenses.sheet_id.filtered(
            lambda x: x.state != "done"
        )
        paid_expenses = not_paid_expenses.filtered(
            lambda expense: expense.currency_id.is_zero(expense.amount_residual)
        )
        paid_expenses.write({"state": "done"})
        paid_sheets = not_paid_expense_sheets.filtered(
            lambda x: all(expense.state == "done" for expense in x.expense_line_ids)
        )
        paid_sheets.set_to_paid()
        return res
