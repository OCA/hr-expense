# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HrExpense(models.Model):

    _inherit = "hr.expense"

    def _get_account_move_line_values(self):
        move_line_values_by_expense = {}
        for expense in self:
            move_line_values = []
            for dis in expense.sheet_id.expense_distribution_ids:
                move_line_name = (
                    expense.employee_id.name + ": " + expense.name.split("\n")[0][:64]
                )
                account_src = expense._get_expense_account_source()
                account_dst = expense._get_expense_account_destination()
                account_date = (
                    expense.sheet_id.accounting_date
                    or expense.date
                    or fields.Date.context_today(expense)
                )

                company_currency = expense.company_id.currency_id

                new_amount = expense.unit_amount * (dis.percentage / 100)
                taxes = expense.tax_ids.with_context(round=True).compute_all(
                    new_amount,
                    expense.currency_id,
                    expense.quantity,
                    expense.product_id,
                )
                total_amount = 0.0
                total_amount_currency = 0.0
                partner_id = (
                    expense.employee_id.sudo().address_home_id.commercial_partner_id.id
                )

                # source move line
                balance = expense.currency_id._convert(
                    taxes["total_excluded"],
                    company_currency,
                    expense.company_id,
                    account_date,
                )
                amount_currency = taxes["total_excluded"]
                move_line_src = {
                    "name": move_line_name,
                    "quantity": expense.quantity or 1,
                    "debit": balance if balance > 0 else 0,
                    "credit": -balance if balance < 0 else 0,
                    "amount_currency": amount_currency,
                    "account_id": account_src.id,
                    "product_id": expense.product_id.id,
                    "product_uom_id": expense.product_uom_id.id,
                    "analytic_account_id": dis.analytic_account_id.id,
                    "analytic_tag_ids": [(6, 0, expense.analytic_tag_ids.ids)],
                    "expense_id": expense.id,
                    "partner_id": partner_id,
                    "tax_ids": [(6, 0, expense.tax_ids.ids)],
                    "tax_tag_ids": [(6, 0, taxes["base_tags"])],
                    "currency_id": expense.currency_id.id,
                }
                move_line_values.append(move_line_src)
                total_amount -= balance
                total_amount_currency -= move_line_src["amount_currency"]

                # taxes move lines
                for tax in taxes["taxes"]:
                    balance = expense.currency_id._convert(
                        tax["amount"],
                        company_currency,
                        expense.company_id,
                        account_date,
                    )
                    amount_currency = tax["amount"]

                    if tax["tax_repartition_line_id"]:
                        rep_ln = self.env["account.tax.repartition.line"].browse(
                            tax["tax_repartition_line_id"]
                        )
                        base_amount = self.env[
                            "account.move"
                        ]._get_base_amount_to_display(tax["base"], rep_ln)
                    else:
                        base_amount = None

                    move_line_tax_values = {
                        "name": tax["name"],
                        "quantity": 1,
                        "debit": balance if balance > 0 else 0,
                        "credit": -balance if balance < 0 else 0,
                        "amount_currency": amount_currency,
                        "account_id": tax["account_id"] or move_line_src["account_id"],
                        "tax_repartition_line_id": tax["tax_repartition_line_id"],
                        "tax_tag_ids": tax["tag_ids"],
                        "tax_base_amount": base_amount,
                        "expense_id": expense.id,
                        "partner_id": partner_id,
                        "currency_id": expense.currency_id.id,
                        "analytic_account_id": expense.analytic_account_id.id
                        if tax["analytic"]
                        else False,
                        "analytic_tag_ids": [(6, 0, expense.analytic_tag_ids.ids)]
                        if tax["analytic"]
                        else False,
                    }
                    total_amount -= balance
                    total_amount_currency -= move_line_tax_values["amount_currency"]
                    move_line_values.append(move_line_tax_values)

                # destination move line
                move_line_dst = {
                    "name": move_line_name,
                    "debit": total_amount > 0 and total_amount,
                    "credit": total_amount < 0 and -total_amount,
                    "account_id": account_dst,
                    "date_maturity": account_date,
                    "amount_currency": total_amount_currency,
                    "currency_id": expense.currency_id.id,
                    "expense_id": expense.id,
                    "partner_id": partner_id,
                }
                move_line_values.append(move_line_dst)

            move_line_values_by_expense[expense.id] = move_line_values
        return move_line_values_by_expense
