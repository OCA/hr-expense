# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    price_tax = fields.Float(
        compute="_compute_amount_price_tax",
        store=True,
        readonly=False,
    )
    tax_adjust = fields.Boolean(
        copy=False,
        help="trigger line with adjust tax",
    )

    def _get_expense_price_tax(self):
        """Common function get price tax"""
        amount = self.unit_amount if self.product_has_cost else self.total_amount
        taxes = self.tax_ids.compute_all(
            amount,
            self.currency_id,
            self.quantity,
            self.product_id,
            self.employee_id.user_id.partner_id,
        )
        return sum(t.get("amount", 0.0) for t in taxes.get("taxes", []))

    @api.depends("currency_id", "tax_ids", "total_amount", "unit_amount", "quantity")
    def _compute_amount_price_tax(self):
        for expense in self.filtered(lambda l: not l.tax_adjust):
            price_tax = expense._get_expense_price_tax()
            expense.price_tax = price_tax

    @api.onchange("price_tax", "tax_ids", "total_amount", "unit_amount", "quantity")
    def _onchange_price_tax(self):
        for expense in self:
            price_tax = expense._get_expense_price_tax()
            expense.tax_adjust = expense.price_tax != price_tax

    @api.depends("quantity", "unit_amount", "tax_ids", "currency_id", "price_tax")
    def _compute_amount(self):
        """Update the total amount to include any applicable taxes
        for products that have a cost. In the core Odoo implementation,
        this adjustment is invisible. This function supports making the adjustment visible
        by overwriting the relevant field.
        """
        res = super()._compute_amount()
        for expense in self.filtered(lambda l: l.unit_amount and l.tax_adjust):
            if expense.tax_ids.filtered(lambda l: not l.price_include):
                price_tax = expense._get_expense_price_tax()
                expense.total_amount -= price_tax - expense.price_tax
        return res

    def _get_expense_balance(self, amount, account_date):
        return self.currency_id._convert(
            amount, self.company_id.currency_id, self.company_id, account_date
        )

    def _get_account_move_line_values(self):
        """Adjust tax amount in accounting move line"""
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self.filtered(lambda l: l.tax_adjust):
            account_src = expense._get_expense_account_source()
            account_dst = expense._get_expense_account_destination()
            account_date = (
                expense.sheet_id.accounting_date
                or expense.date
                or fields.Date.context_today(expense)
            )
            # Find price diff origin and adjust
            price_tax = expense._get_expense_price_tax()
            diff_price_tax_currency = price_tax - expense.price_tax
            diff_price_tax = expense._get_expense_balance(
                diff_price_tax_currency, account_date
            )
            first_line_tax = False
            # NOTE: Core odoo value `move_line_values_by_expense` sort by
            # source move line, taxes move lines and destination move line in order.
            for move_line_values in move_line_values_by_expense[expense.id]:
                # Tax adjust move line. if multi tax, we compute with first line tax only
                if "tax_base_amount" in move_line_values:
                    if first_line_tax:
                        continue
                    new_tax_amount = move_line_values["debit"] - diff_price_tax
                    move_line_values.update(
                        {
                            "debit": new_tax_amount if new_tax_amount > 0 else 0,
                            # move to credit, if adjust tax more than tax calculate
                            "credit": abs(new_tax_amount) if new_tax_amount < 0 else 0,
                            "amount_currency": move_line_values["amount_currency"]
                            - diff_price_tax_currency,
                        }
                    )
                    first_line_tax = True
                    continue
                # Source move line, For case include price
                if (
                    expense.tax_ids.filtered("price_include")
                    and move_line_values.get("account_id") == account_src.id
                ):
                    move_line_values.update(
                        {
                            "debit": move_line_values["debit"] + diff_price_tax
                            if move_line_values["debit"] > 0
                            else 0,
                            "credit": move_line_values["credit"] + diff_price_tax
                            if move_line_values["credit"] > 0
                            else 0,
                            "amount_currency": move_line_values["amount_currency"]
                            + diff_price_tax_currency,
                        }
                    )
                # Destination adjust move line, For case exclude price
                elif (
                    not expense.tax_ids.filtered("price_include")
                    and move_line_values.get("account_id") == account_dst
                ):
                    move_line_values.update(
                        {
                            "debit": move_line_values["debit"] - diff_price_tax
                            if move_line_values["debit"] > 0
                            else 0,
                            "credit": move_line_values["credit"] - diff_price_tax
                            if move_line_values["credit"] > 0
                            else 0,
                            "amount_currency": move_line_values["amount_currency"]
                            - diff_price_tax_currency,
                        }
                    )
        return move_line_values_by_expense
