# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_hr_expense_widget_o2m = fields.Boolean(
        string="Use form view when add line for expense report",
        implied_group="hr_expense_widget_o2m.group_hr_expense_widget_o2m",
    )
