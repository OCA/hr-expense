# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    payment_ids = fields.Many2many(
        comodel_name="account.payment",
        relation="payment_expense_sheet_rel",
        column1="sheet_id",
        column2="payment_id",
        string="Payment",
        readonly=True,
        copy=False,
    )

    def action_register_payment(self):
        """Send context when you register payment from expense sheet"""
        action = super().action_register_payment()
        if self._name == "hr.expense.sheet":
            action["context"].update({"expense_sheet_ids": self.ids})
        return action
