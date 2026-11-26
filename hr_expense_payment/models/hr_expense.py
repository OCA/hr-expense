# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


def domain_value_ids(value):
    """Return the truthy ids held by a domain value, empty for "is not set"."""
    if value is None or isinstance(value, (int, bool)):
        candidates = [value]
    else:
        candidates = list(value)
    return [candidate for candidate in candidates if candidate]


class HrExpense(models.Model):
    _inherit = "hr.expense"

    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        string="Payments",
        compute="_compute_payment_ids",
        compute_sudo=True,
        search="_search_payment_ids",
        help="Payments linked to this expense's journal entry, whether "
        "reconciled with it or matched by the payment register.",
    )

    payment_count = fields.Integer(
        string="Payments Count", compute="_compute_payment_count", compute_sudo=True
    )

    @api.depends(
        "account_move_id.line_ids.matched_debit_ids",
        "account_move_id.line_ids.matched_credit_ids",
        "account_move_id.matched_payment_ids",
    )
    def _compute_payment_ids(self):
        for expense in self:
            expense.payment_ids = expense.account_move_id.reconciled_payment_ids

    @api.depends("payment_ids")
    def _compute_payment_count(self):
        for expense in self:
            expense.payment_count = len(expense.payment_ids)

    def action_open_payments(self):
        """Open the payments reimbursing the selected expenses."""
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Payments"),
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("reconciled_expense_ids", "in", self.ids)],
            "context": {"create": False},
        }

    def _search_payment_ids(self, operator, value):
        if operator not in ("in", "="):
            return NotImplemented
        payment_ids = domain_value_ids(value)
        if not payment_ids:
            unpaid_moves = self.search(
                [("account_move_id", "!=", False)]
            ).account_move_id.filtered(lambda move: not move.reconciled_payment_ids)
            return [
                "|",
                ("account_move_id", "=", False),
                ("account_move_id", "in", unpaid_moves.ids),
            ]
        payments = self.env["account.payment"].browse(payment_ids)
        return [("id", "in", payments.reconciled_expense_ids.ids)]
