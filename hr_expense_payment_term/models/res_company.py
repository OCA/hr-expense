# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_accounting_current_date = fields.Boolean(
        string="Accounting with the current date",
        help="If checked, accounting date on expense will be "
        "current date instead of expense date.",
    )
