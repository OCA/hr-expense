# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hr_trip_require_approval = fields.Boolean(
        string="Require Trip Approval",
        config_parameter="hr_expense_trip.require_approval",
    )
