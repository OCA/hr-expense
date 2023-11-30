# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    expense_sheet_ids = fields.Many2many(
        comodel_name="hr.expense.sheet",
        relation="payment_expense_sheet_rel",
        column1="payment_id",
        column2="sheet_id",
        string="Expense sheet",
        readonly=True,
        copy=False,
    )
