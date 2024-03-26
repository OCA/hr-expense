# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
from collections import defaultdict

from odoo import api, fields, models
from odoo.tools.misc import formatLang


class HrExpense(models.Model):
    _inherit = "hr.expense"

    tax_amount = fields.Float(
        digits="Account",
        string="Tax",
        compute="_compute_tax_amount",
        store=True,
        readonly=False,
    )
    amount_by_group = fields.Binary(
        string="Tax amount by group",
        compute="_compute_amount_by_group",
        help="Edit Tax amounts if you encounter rounding issues.",
    )
    amount_by_group_txt = fields.Text(
        string="Tax Amount Text",
        default="[]",
        compute="_compute_expense_taxes_by_group",
        store=True,
        readonly=False,
    )
    editable_tax_adjustment = fields.Boolean(
        compute="_compute_editable_tax_adjustment",
        string="Edit Tax Adjustment",
    )

    @api.depends("state", "sheet_id.state")
    def _compute_editable_tax_adjustment(self):
        """Editable tax adjustment on expense state
        'Draft', 'Submited' and 'Approved'"""
        for rec in self:
            rec.editable_tax_adjustment = (
                (
                    rec.sheet_id.state in ["draft", "submit", "approve"]
                    or rec.state == "draft"
                )
                and True
                or False
            )

    @api.depends("amount_by_group_txt")
    def _compute_amount_by_group(self):
        for expense in self:
            expense.amount_by_group = ast.literal_eval(
                expense.amount_by_group_txt or "[]"
            )

    @api.depends("amount_by_group")
    def _compute_tax_amount(self):
        for expense in self:
            tax_amount = 0.0
            for amount_line in expense.amount_by_group:
                tax_amount += amount_line[1]
            expense.tax_amount = tax_amount

    @api.depends("quantity", "unit_amount", "tax_ids", "currency_id", "tax_amount")
    def _compute_amount(self):
        """Override the `_compute_amount()`."""
        self._compute_tax_amount()  # Make sure that tax_amount updated
        for expense in self:
            taxes = expense.tax_ids.with_context(round=True).compute_all(
                expense.unit_amount,
                expense.currency_id,
                expense.quantity,
                expense.product_id,
                expense.employee_id.user_id.partner_id,
            )
            expense.untaxed_amount = taxes.get("total_excluded", 0.0)
            expense.total_amount = expense.untaxed_amount + expense.tax_amount

    @api.depends("quantity", "unit_amount", "tax_ids", "currency_id", "employee_id")
    def _compute_expense_taxes_by_group(self):
        for expense in self:
            partner_id = expense.employee_id.user_id.partner_id
            lang_env = expense.with_context(lang=partner_id.lang).env
            taxes = expense.tax_ids.with_context(round=True).compute_all(
                expense.unit_amount,
                expense.currency_id,
                expense.quantity,
                expense.product_id,
                expense.employee_id.user_id.partner_id,
            )
            base_amount = taxes.get("total_excluded", 0.0)

            tax_group_mapping = defaultdict(
                lambda: {
                    "base_amount": base_amount,
                    "tax_amount": 0.0,
                    "tax_name": "",
                }
            )

            for tax in expense.tax_ids.flatten_taxes_hierarchy():
                tax_group_vals = tax_group_mapping[tax.id]
                tax_group_vals["tax_name"] = tax.name
            for tax_line in taxes["taxes"]:
                tax_id = tax_line["id"]
                tax_group_vals = tax_group_mapping[tax_id]
                tax_group_vals["tax_amount"] += tax_line["amount"]
            amount_by_group = []
            for tax_group in tax_group_mapping.keys():
                tax_group_vals = tax_group_mapping[tax_group]
                if isinstance(tax_group, models.NewId):
                    tax_group = tax_group.origin
                amount_by_group_str = "['{}', {}, {}, '{}', '{}', {}, {}]".format(
                    tax_group_vals["tax_name"],
                    tax_group_vals["tax_amount"],
                    tax_group_vals["base_amount"],
                    formatLang(
                        lang_env,
                        tax_group_vals["tax_amount"],
                        currency_obj=expense.currency_id,
                    ),
                    formatLang(
                        lang_env,
                        tax_group_vals["base_amount"],
                        currency_obj=expense.currency_id,
                    ),
                    len(tax_group_mapping),
                    tax_group,
                )
                amount_by_group.append(amount_by_group_str)
            expense.amount_by_group_txt = "[{}]".format(", ".join(amount_by_group))

    # def _get_expense_account_destination(self):
    #     self.ensure_one()
    #     # support module `hr_expense_advance_clearing` for case clearing
    #     if (
    #         self.sheet_id._fields.get("advance_sheet_id", False)
    #         and self.sheet_id.advance_sheet_id
    #     ):
    #         account_dest = self.env["account.account"]
    #         if not self.employee_id.sudo().address_home_id:
    #             raise UserError(
    #                 _(
    #                     "No Home Address found for the employee %s, please configure one."
    #                 )
    #                 % (self.employee_id.name)
    #             )
    #         partner = self.employee_id.sudo().address_home_id.with_company(
    #             self.company_id
    #         )
    #         # clearing is reverse payable to receivable
    #         account_dest = (
    #             partner.property_account_receivable_id.id
    #             or partner.parent_id.property_account_receivable_id.id
    #         )
    #         return account_dest
    #     return super()._get_expense_account_destination()

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            # Prepare data
            account_dst = expense._get_expense_account_destination()
            account_date = (
                expense.sheet_id.accounting_date
                or expense.date
                or fields.Date.context_today(expense)
            )
            company_currency = expense.company_id.currency_id
            new_tax_amount = 0.0
            old_tax_amount = 0.0
            amount_by_group = dict()
            for amount_line in expense.amount_by_group:
                amount_by_group[amount_line[0]] = amount_line[1]

            # Update move_line_values_by_expense
            for line in move_line_values_by_expense[expense.id]:
                # taxes move lines
                if line["name"] in amount_by_group.keys():
                    tax = amount_by_group[line["name"]]
                    balance = expense.currency_id._convert(
                        tax, company_currency, expense.company_id, account_date
                    )
                    old_tax_amount += line["amount_currency"]
                    new_tax_amount += balance
                    line.update(
                        {
                            "debit": balance if balance > 0 else 0,
                            "credit": -balance if balance < 0 else 0,
                            "amount_currency": balance,
                        }
                    )
                # destination move line
                if line["account_id"] == account_dst:
                    debit = line["debit"] or 0
                    credit = line["credit"] or 0
                    amount = debit - credit
                    old_tax_amount = expense.currency_id._convert(
                        old_tax_amount,
                        company_currency,
                        expense.company_id,
                        account_date,
                    )
                    balance = amount + (old_tax_amount - new_tax_amount)
                    line.update(
                        {
                            "debit": balance if balance > 0 else 0,
                            "credit": -balance if balance < 0 else 0,
                            "amount_currency": balance,
                        }
                    )
        return move_line_values_by_expense
