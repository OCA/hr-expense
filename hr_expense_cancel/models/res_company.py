# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    expense_payment_cancel = fields.Selection(
        string="Payment Cancel",
        selection=[
            ("post", "Posted"),
            ("cancel", "Refused"),
        ],
        default="cancel",
        help="Select the state expense policy after you cancel payment",
    )
    expense_move_cancel = fields.Selection(
        string="Account Move Cancel",
        selection=[
            ("submit", "Submit"),
            ("approve", "Approve"),
            ("cancel", "Refused"),
        ],
        default="cancel",
        help="Select the state expense policy after you cancel move",
    )
