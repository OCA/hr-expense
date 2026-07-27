# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    reconciled_expense_ids = fields.Many2many(
        comodel_name="hr.expense",
        string="Reimbursed Expenses",
        compute="_compute_reconciled_expense_ids",
        compute_sudo=True,
        search="_search_reconciled_expense_ids",
        help="Employee-paid expenses whose journal entry is linked to this "
        "payment, by reconciliation or by the payment register.",
    )

    @api.depends(
        "invoice_ids",
        "move_id.line_ids.matched_debit_ids",
        "move_id.line_ids.matched_credit_ids",
    )
    def _compute_reconciled_expense_ids(self):
        for payment in self:
            payment.reconciled_expense_ids = (
                payment.invoice_ids | payment.reconciled_bill_ids
            ).expense_ids

    def _search_reconciled_expense_ids(self, operator, value):
        if operator not in ("in", "="):
            return NotImplemented
        expenses = self.env["hr.expense"].browse(value)
        return [("id", "in", expenses.payment_ids.ids)]
