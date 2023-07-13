# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    advance = fields.Boolean(string="Employee Advance", default=False)
    clearing_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Clearing Product",
        tracking=True,
        domain="[('can_be_expensed', '=', True),"
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete="restrict",
        help="Optional: On the clear advance, the clearing "
        "product will create default product line.",
    )
    av_line_id = fields.Many2one(
        comodel_name="hr.expense",
        string="Ref: Advance",
        ondelete="set null",
        help="Expense created from this advance expense line",
    )

    @api.constrains("advance")
    def _check_advance(self):
        for expense in self.filtered("advance"):
            emp_advance = self.env.ref(
                "hr_expense_advance_clearing.product_emp_advance"
            )
            if not emp_advance.property_account_expense_id:
                raise ValidationError(
                    _("Employee advance product has no payable account")
                )
            if expense.product_id != emp_advance:
                raise ValidationError(
                    _("Employee advance, selected product is not valid")
                )
            if expense.account_id != emp_advance.property_account_expense_id:
                raise ValidationError(
                    _("Employee advance, account must be the same payable account")
                )
            if expense.tax_ids:
                raise ValidationError(_("Employee advance, all taxes must be removed"))
            if expense.payment_mode != "own_account":
                raise ValidationError(_("Employee advance, paid by must be employee"))
        return True

    @api.onchange("advance")
    def onchange_advance(self):
        self.tax_ids = False
        if self.advance:
            self.product_id = self.env.ref(
                "hr_expense_advance_clearing.product_emp_advance"
            )

    # =================================

    # def _get_expense_account_destination(self):
    #     self.ensure_one()
    #     if self.sheet_id.advance_sheet_id and self.payment_mode != "company_account":
    #         emp_advance = self.env.ref(
    #             "hr_expense_advance_clearing.product_emp_advance"
    #         )
    #         account_dest = emp_advance.property_account_expense_id
    #         return account_dest.id or super()._get_expense_account_destination()
    #     else:
    #         return super()._get_expense_account_destination()
