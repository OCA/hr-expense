# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    clearing_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Default Clearing Journal",
        check_company=True,
        domain="[('type', '=', 'general')]",
        help="Default Miscellaneous journal used when posting the advance "
        "clearing journal entry.",
    )
