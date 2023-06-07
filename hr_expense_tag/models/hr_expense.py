# Copyright 2023 ForgeFlow
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpense(models.Model):

    _inherit = "hr.expense"

    tag_ids = fields.Many2many("hr.expense.tag", string="Tags")
