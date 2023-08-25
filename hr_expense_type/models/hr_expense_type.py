# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class HrExpenseSheetType(models.Model):
    _name = "hr.expense.type"
    _description = "Type of expense sheet"
    _order = "sequence"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    description = fields.Text(translate=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
