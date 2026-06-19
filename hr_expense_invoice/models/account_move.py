# Copyright 2019 Ecosoft <saranl@ecosoft.co.th>
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    # Expenses that reference this bill via invoice_id (distinct from core's
    # receipt-flow expense_ids).
    invoice_expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="invoice_id",
        string="Linked Expenses",
    )
    source_invoice_expense_id = fields.Many2one(
        comodel_name="hr.expense",
        help="Expense that owns this AP transfer entry "
        "(employee-paid bill-linked path).",
    )

    @api.constrains("amount_total")
    def _check_invoice_expense_ids(self):
        precision = self.env["decimal.precision"].precision_get("Product Price")
        for move in self.filtered("invoice_expense_ids"):
            expense_amount = sum(
                move.invoice_expense_ids.mapped("total_amount_currency")
            )
            if float_compare(expense_amount, move.amount_total, precision) != 0:
                raise ValidationError(
                    self.env._(
                        "You can't change the total amount, as there's an "
                        "expense linked to this invoice."
                    )
                )

    def action_view_invoice_expense(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.expense",
            "res_id": self.invoice_expense_ids[:1].id,
        }

    def action_force_register_payment(self):
        if not self.source_invoice_expense_id:
            return super().action_force_register_payment()
        return self.line_ids.action_register_payment()


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.constrains("account_id", "display_type")
    def _check_payable_receivable(self):
        # Expense-linked lines may legitimately mix payable/receivable
        # accounts; skip the core check for those.
        _self = self.filtered("expense_id")
        return super(AccountMoveLine, (self - _self))._check_payable_receivable()

    def reconcile(self):
        """Refresh the linked expense's residual once the transfer entry is
        reconciled (bill paid -> employee reimbursed)."""
        source_expenses = self.move_id.source_invoice_expense_id
        not_paid = source_expenses.filtered(lambda x: x.amount_residual)
        res = super().reconcile()
        for expense in not_paid:
            if expense.currency_id.is_zero(expense.amount_residual):
                expense.invalidate_recordset(["amount_residual"])
        return res
