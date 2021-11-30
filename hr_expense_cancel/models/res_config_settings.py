# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    expense_cancel_policy = fields.Selection(
        related="company_id.expense_cancel_policy",
        readonly=False,
        required=True,
        help="""Select the policy journal entries following,
        'Unlink' -> Remove journal entries
        'Cancel' -> Cancel journal entries
        """,
    )
    expense_cancel_state = fields.Selection(
        related="company_id.expense_cancel_state",
        readonly=False,
        required=True,
        help="Select the state policy after you cancel on expense",
    )
