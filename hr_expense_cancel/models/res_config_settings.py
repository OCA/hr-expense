# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    payment_cancel_policy = fields.Selection(
        related="company_id.payment_cancel_policy",
        readonly=False,
        required=True,
        help="Select the state expense policy after you cancel payment",
    )
    je_cancel_policy = fields.Selection(
        related="company_id.je_cancel_policy",
        readonly=False,
        required=True,
        help="Select the state expense policy after you cancel journal entries",
    )
    ex_cancel_policy = fields.Selection(
        related="company_id.ex_cancel_policy",
        readonly=False,
        required=True,
        help="Select the state expense policy after you cancel expense",
    )
