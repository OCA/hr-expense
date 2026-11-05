# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_intermediate_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Intermediate Expense Journal",
        check_company=True,
        domain=[("type", "=", "general")],
        help="Journal used to record intermediate entries for employee expenses.\n"
        "If not set, Expense Journal will be used instead.",
    )
