# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    auto_refresh_account_moves = fields.Boolean(
        string="Auto Sync Expense Moves",
        default=False,
        help="When enabled, editing an approved expense automatically "
        "regenerates the linked draft journal entries to stay in sync.",
    )
