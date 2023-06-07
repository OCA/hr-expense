# Copyright 2023 ForgeFlow
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpenseSheet(models.Model):

    _inherit = "hr.expense.sheet"

    tag_ids = fields.Many2many("crm.tag", string="Tags")
