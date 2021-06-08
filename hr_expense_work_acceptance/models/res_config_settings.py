# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    group_enable_wa_on_exp = fields.Boolean(
        string="Enable WA on Expense Sheet",
        implied_group="hr_expense_work_acceptance.group_enable_wa_on_exp",
    )
    group_wa_accepted_before_inv = fields.Boolean(
        string="WA Accepted before Accounting",
        implied_group="hr_expense_work_acceptance.group_wa_accepted_before_inv",
    )
