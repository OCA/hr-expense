# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    expense_sheet_id = fields.Many2one(related="move_id.expense_sheet_id")

    def action_open_expense_report(self):
        self.ensure_one()
        return self.expense_sheet_id._get_records_action()
