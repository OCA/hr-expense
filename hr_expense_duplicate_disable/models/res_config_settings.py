# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hr_expense_disable_duplicate_detection = fields.Boolean(
        string="Disable duplicate expense detection",
        config_parameter="hr_expense_disable_duplicate_detection",
        help="If enabled, the system will not warn about duplicate expenses.",
    )
