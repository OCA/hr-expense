from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_sheet_id = fields.Many2one(
        "hr.expense.sheet",
        string="Expense Report",
        help="Expense sheet from which this vendor bill was created.",
        ondelete="set null",
    )

    is_employee_reimbursement = fields.Boolean(
        string="Employee reimbursement",
        default=False,
        help="Marks vendor bills created by hr_expense_vendor_bill.",
    )

    def _compute_payment_state(self):
        res = super()._compute_payment_state()

        reembolsos = self.filtered(lambda m: m.is_employee_reimbursement)
        for move in reembolsos:
            move.payment_state = "not_paid"

        return res
