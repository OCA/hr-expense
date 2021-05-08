# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HRExpense(models.Model):
    _inherit = "hr.expense"

    advance_line = fields.One2many(
        comodel_name="hr.expense.advance.line", inverse_name="expense_id"
    )

    @api.constrains("total_amount", "advance_line")
    def _check_amount_total(self):
        for exp in self:
            advance_detail_amount = sum(exp.advance_line.mapped("unit_amount"))
            if exp.advance and exp.total_amount != advance_detail_amount:
                raise UserError(_("Amount Detail Advance not equal Total Amount"))
