# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    READONLY_STATES = {
        "post": [("readonly", True)],
        "done": [("readonly", True)],
        "cancel": [("readonly", True)],
    }
    expense_date_due = fields.Date(
        string="Due Date",
        index=True,
        copy=False,
        states=READONLY_STATES,
    )
    expense_payment_term_id = fields.Many2one(
        comodel_name="account.payment.term",
        compute="_compute_expense_payment_term",
        store=True,
        readonly=False,
        string="Payment Terms",
        check_company=True,
        states=READONLY_STATES,
    )

    @api.depends("employee_id")
    def _compute_expense_payment_term(self):
        for rec in self:
            partner_id = rec.employee_id.address_home_id
            rec.expense_payment_term_id = (
                partner_id.property_supplier_payment_term_id or False
            )

    @api.onchange("accounting_date")
    def _onchange_accounting_date(self):
        if (
            self.accounting_date
            and not self.expense_payment_term_id
            and (
                not self.expense_date_due
                or self.expense_date_due < self.accounting_date
            )
        ):
            self.expense_date_due = self.accounting_date

    def action_sheet_move_create(self):
        # compute accounting date from current date
        if self.env.user.company_id.expense_accounting_current_date:
            for sheet in self.filtered(lambda s: not s.accounting_date):
                today = fields.Date.context_today(self)
                sheet.accounting_date = today
        res = super().action_sheet_move_create()
        return res
