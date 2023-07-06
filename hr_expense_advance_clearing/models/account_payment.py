# Copyright 2022 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    advance_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        readonly=True,
    )

    def _synchronize_from_moves(self, changed_fields):
        """skip check when payment is return advance"""
        self = (
            self.with_context(skip_account_move_synchronization=True)
            if self.filtered("advance_id")
            else self
        )
        return super()._synchronize_from_moves(changed_fields)

    @api.depends("expense_sheet_id.advance_sheet_id")
    def _compute_outstanding_account_id(self):
        for pay in self:
            advance = pay.expense_sheet_id.filtered(lambda ad: ad.advance_sheet_id)
            if advance:
                emp_advance = self.env.ref(
                    "hr_expense_advance_clearing.product_emp_advance"
                )
                pay.outstanding_account_id = (
                    emp_advance.property_account_expense_id
                    and emp_advance.property_account_expense_id.id
                    or False
                )
            else:
                return super()._compute_outstanding_account_id()
