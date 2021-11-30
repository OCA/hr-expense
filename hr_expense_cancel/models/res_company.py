# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_cancel_policy = fields.Selection(
        string="Policy",
        selection=[
            ("unlink", "Unlink"),
            ("cancel", "Cancel"),
        ],
        default="unlink",
        help="""Select the policy journal entries following,
        'Unlink' -> Remove journal entries
        'Reverse' -> Reverse journal entries
        'Cancel' -> Cancel journal entries
        """,
    )
    expense_cancel_state = fields.Selection(
        string="Cancel to State",
        selection=[
            ("submit", "Submit"),
            ("approve", "Approve"),
        ],
        default="submit",
        help="Select the state policy after you cancel on expense",
    )
