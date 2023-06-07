# Copyright 2023 ForgeFlow
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from random import randint
from odoo import fields, models


class Tag(models.Model):
    _name = "hr.expense.tag"

    _description = "Expense Tag"

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char('Expense Tag Name', required=True, translate=True)
    color = fields.Integer('Color', default=_get_default_color)
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
