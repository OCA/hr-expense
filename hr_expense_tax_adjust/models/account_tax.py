from odoo import api, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.model
    def _prepare_tax_totals(self, base_lines, currency, tax_lines=None):
        """Update amount untaxed for tax adjust expense"""
        res = super()._prepare_tax_totals(base_lines, currency, tax_lines)
        amount_untaxed = 0.0
        for base_line in base_lines:
            expense = base_line["record"].expense_id
            if expense.tax_adjust:
                amount_untaxed += (
                    expense.total_amount_company - expense.amount_tax_company
                )
        if amount_untaxed:
            res["amount_untaxed"] = amount_untaxed
        return res
