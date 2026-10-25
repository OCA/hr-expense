# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_refresh_account_moves = fields.Boolean(
        related="company_id.auto_refresh_account_moves",
        readonly=False,
    )
