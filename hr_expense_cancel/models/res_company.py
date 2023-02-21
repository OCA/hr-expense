# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    payment_cancel_policy = fields.Selection(
        string="Payment Cancel",
        selection=[
            ("post", "Posted"),
            ("cancel", "Refused"),
        ],
        default="cancel",
        help="Select the state expense policy after you cancel payment",
    )
    je_cancel_policy = fields.Selection(
        string="Journal Entries Cancel",
        selection=[
            ("submit", "Submit"),
            ("approve", "Approve"),
            ("cancel", "Refused"),
        ],
        default="cancel",
        help="Select the state expense policy after you cancel journal entries",
    )
    ex_cancel_policy = fields.Selection(
        string="Expense Cancel",
        selection=[
            ("draft", "Draft"),
            ("submit", "Submitted"),
            ("approve", "Approved"),
        ],
        default="draft",
        help="Select the state expense policy after you cancel expense",
    )
