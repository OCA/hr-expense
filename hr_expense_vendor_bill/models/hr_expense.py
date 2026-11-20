from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    vendor_id = fields.Many2one(
        "res.partner",
        string="Vendor",
        help="Vendor from which this expense originates.",
    )
