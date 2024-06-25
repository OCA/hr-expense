# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    payment_type_id = fields.Many2one("account.journal", string="Payment Journal")

    def _get_default_expense_sheet_values(self):
        context = super()._get_default_expense_sheet_values()
        if self.payment_type_id:
            context["default_bank_journal_id"] = self.payment_type_id.id
        return context
