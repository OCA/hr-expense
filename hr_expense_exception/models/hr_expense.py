# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "base.exception.method"]

    ignore_exception = fields.Boolean(
        related="sheet_id.ignore_exception", store=True, string="Ignore Exceptions"
    )

    def _get_main_records(self):
        return self.mapped("sheet_id")

    @api.model
    def _reverse_field(self):
        return "expense_sheet_ids"

    def _detect_exceptions(self, rule):
        records = super()._detect_exceptions(rule)
        return records.mapped("sheet_id")

    def _detect_exception_get_exc_class_values(self):
        res = super()._detect_exception_get_exc_class_values()
        return dict(res, target_model="hr.expense.sheet")
