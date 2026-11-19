# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    expense_intermediate_journal_id = fields.Many2one(
        comodel_name="account.journal",
        related="company_id.expense_intermediate_journal_id",
        readonly=False,
        check_company=True,
        domain="[('type', '=', 'general')]",
    )
