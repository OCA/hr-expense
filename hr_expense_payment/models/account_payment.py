# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

from .hr_expense import domain_value_ids


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

    reconciled_expense_count = fields.Integer(
        string="Reimbursed Expenses Count",
        compute="_compute_reconciled_expense_count",
        compute_sudo=True,
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

    @api.depends("reconciled_expense_ids")
    def _compute_reconciled_expense_count(self):
        for payment in self:
            payment.reconciled_expense_count = len(payment.reconciled_expense_ids)

    def action_open_reconciled_expenses(self):
        """Open the employee-paid expenses reimbursed by these payments."""
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Reimbursed Expenses"),
            "res_model": "hr.expense",
            "view_mode": "list,form",
            "domain": [("payment_ids", "in", self.ids)],
            "context": {"create": False},
        }

    def _search_reconciled_expense_ids(self, operator, value):
        if operator not in ("in", "="):
            return NotImplemented
        expense_ids = domain_value_ids(value)
        if not expense_ids:
            reimbursing = (
                self.env["hr.expense"]
                .search([("account_move_id", "!=", False)])
                .account_move_id.reconciled_payment_ids
            )
            return [("id", "not in", reimbursing.ids)]
        expenses = self.env["hr.expense"].browse(expense_ids)
        return [("id", "in", expenses.payment_ids.ids)]
