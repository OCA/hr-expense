# Copyright 2026 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        string="Payment Terms",
        check_company=True,
    )
    invoice_date_due = fields.Date(string="Due Date")

    def _prepare_bill_vals(self):
        vals = super()._prepare_bill_vals()
        if self.payment_term_id:
            vals["invoice_payment_term_id"] = self.payment_term_id.id
        elif self.invoice_date_due:
            vals["invoice_date_due"] = self.invoice_date_due
        return vals
