# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpenseAdvanceLine(models.Model):
    _name = "hr.expense.advance.line"
    _description = "Details of employee advance"

    sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        required=True,
        index=True,
        ondelete="cascade",
    )
    av_line_id = fields.Many2one(
        comodel_name="hr.expense",
        help="Refer to original advance. Line with this value is considered a temp line",
    )
    name = fields.Char(string="Description", required=True)
    currency_id = fields.Many2one(related="sheet_id.currency_id")
    unit_amount = fields.Monetary(string="Unit Price", currency_field="currency_id")
