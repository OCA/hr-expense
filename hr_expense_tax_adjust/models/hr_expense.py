# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    tax_adjust = fields.Boolean(
        copy=False,
        help="trigger line with adjust tax",
    )

    @api.depends(
        "currency_rate",
        "total_amount",
        "tax_ids",
        "product_id",
        "employee_id.user_id.partner_id",
        "quantity",
        "amount_tax_company",
    )
    def _compute_total_amount_company(self):
        """Update amount_tax when adjust tax"""
        expense_tax_adjust = self.filtered(lambda l: l.tax_adjust)
        res = super(
            HrExpense, self - expense_tax_adjust
        )._compute_total_amount_company()
        for expense in expense_tax_adjust:
            base_lines = [
                expense._convert_to_tax_base_line_dict(
                    price_unit=expense.total_amount * expense.currency_rate,
                    currency=expense.company_currency_id,
                )
            ]
            taxes_totals = self.env["account.tax"]._compute_taxes(base_lines)["totals"][
                expense.company_currency_id
            ]
            expense.total_amount_company = (
                taxes_totals["amount_untaxed"] + taxes_totals["amount_tax"]
            )
            # Use same as adjust tax
            if expense.same_currency:
                amount_tax_company = expense.amount_tax
            # Convert amount_tax to company currency
            else:
                amount_tax_company = expense.currency_id._convert(
                    expense.amount_tax,
                    expense.company_id.currency_id,
                    expense.company_id,
                    expense.date,
                )
            expense.amount_tax_company = amount_tax_company
        return res

    @api.depends("total_amount", "tax_ids", "currency_id")
    def _compute_amount_tax(self):
        """Do not update amount_tax when adjust tax"""
        expense_tax_adjust = self.filtered(lambda l: l.tax_adjust)
        res = super(HrExpense, self - expense_tax_adjust)._compute_amount_tax()
        for expense in expense_tax_adjust:
            base_lines = [
                expense._convert_to_tax_base_line_dict(price_unit=expense.total_amount)
            ]
            taxes_totals = self.env["account.tax"]._compute_taxes(base_lines)["totals"][
                expense.currency_id
            ]
            expense.untaxed_amount = taxes_totals["amount_untaxed"]
        return res
