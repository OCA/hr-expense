# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    clearing_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.clearing_journal_id",
        check_company=True,
        domain="[('type', '=', 'general')]",
        readonly=False,
    )
