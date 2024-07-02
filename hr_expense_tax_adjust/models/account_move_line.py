from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.depends("quantity", "discount", "price_unit", "tax_ids", "currency_id")
    def _compute_totals(self):
        """Update amount untaxed for tax adjust expense"""
        ml_expense = self.filtered(lambda l: l.expense_id.tax_adjust)
        res = super()._compute_totals()
        for line in ml_expense:
            expense = line.expense_id
            if line.tax_line_id:
                line.tax_base_amount = (
                    expense.total_amount_company - expense.amount_tax_company
                )
                line.amount_currency = expense.amount_tax_company
            else:
                line.price_subtotal = (
                    expense.total_amount_company - expense.amount_tax_company
                )
        return res
