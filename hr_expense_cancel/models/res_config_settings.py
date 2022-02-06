# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    expense_payment_cancel = fields.Selection(
        related="company_id.expense_payment_cancel",
        readonly=False,
        required=True,
        help="Select the state expense policy after you cancel payment",
    )
    expense_move_cancel = fields.Selection(
        related="company_id.expense_move_cancel",
        readonly=False,
        required=True,
        help="Select the state expense policy after you cancel expense",
    )
