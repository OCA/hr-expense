# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HRExpense(models.Model):
    _inherit = "hr.expense"

    av_line_id = fields.Many2one(
        comodel_name="hr.expense",
        ondelete="set null",
        help="Expense created from this advance expense line",
    )
