# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    selectable_payment_method_line_ids = fields.Many2many(
        comodel_name="account.payment.method.line",
        compute="_compute_selectable_payment_method_line_ids",
    )
    payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Payment Method",
        domain="[('id', 'in', selectable_payment_method_line_ids)]",
        help="The payment method used when the expense is paid by the company.",
    )

    @api.depends("company_id")
    def _compute_selectable_payment_method_line_ids(self):
        for sheet in self:
            allowed_method_line_ids = (
                sheet.company_id.company_expense_allowed_payment_method_line_ids
            )
            if allowed_method_line_ids:
                sheet.selectable_payment_method_line_ids = allowed_method_line_ids
            else:
                sheet.selectable_payment_method_line_ids = self.env[
                    "account.payment.method.line"
                ].search(
                    [
                        ("payment_type", "=", "outbound"),
                        ("company_id", "parent_of", sheet.company_id.id),
                    ]
                )

    def _get_default_expense_sheet_values(self):
        values = super()._get_default_expense_sheet_values()
        if self.payment_method_line_id:
            for val in values:
                val["payment_method_line_id"] = self.payment_method_line_id.id
        return values
