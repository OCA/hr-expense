# Copyright 2021 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _get_account_move_line_values(self):
        # As the move linked to an expense sheet is of type entry, we need
        # to manually exclude the payable line from 'invoice tab' to ensure
        # the payment_state is computed correctly as it is on vendor bills.
        result = super()._get_account_move_line_values()
        for expense_id, values in result.items():
            expense = self.browse(expense_id)
            account_dest_id = expense._get_expense_account_destination()
            for val in values:
                if val["account_id"] == account_dest_id:
                    val.update({"exclude_from_invoice_tab": True})
        return result


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    payment_state = fields.Selection(
        [
            ("not_paid", "Not Paid"),
            ("in_payment", "In Payment"),
            ("paid", "Paid"),
            ("partial", "Partially Paid"),
            ("reversed", "Reversed"),
            ("invoicing_legacy", "Invoicing App Legacy"),
        ],
        string="Payment Status",
        store=True,
        readonly=True,
        copy=False,
        tracking=True,
        compute="_compute_payment_state",
    )

    @api.depends("account_move_id.payment_state")
    def _compute_payment_state(self):
        for sheet in self:
            sheet.payment_state = sheet.account_move_id.payment_state or "not_paid"
