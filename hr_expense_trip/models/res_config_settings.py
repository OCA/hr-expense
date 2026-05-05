# Copyright 2024 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    hr_trip_auto_approve = fields.Boolean(
        string="Auto Approve Trip Requests",
        config_parameter="hr_expense_trip.auto_approve",
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        params = self.env["ir.config_parameter"].sudo()
        value = params.get_param("hr_expense_trip.auto_approve")
        # Default to True when the parameter has never been set
        res["hr_trip_auto_approve"] = value != "False" if value else True
        return res
