# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _prepare_payment_expense_company(
        self,
        payment_methods,
        journal,
        different_currency,
        journal_currency,
        total_amount_currency,
    ):
        self.ensure_one()
        commercial_partner_id = (
            self.employee_id.sudo().address_home_id.commercial_partner_id
        )
        payment_dict = {
            "date": self.date,
            "amount": total_amount_currency,
            "payment_type": "outbound",
            "partner_type": "supplier",
            "ref": self.name,
            "journal_id": journal.id,
            "currency_id": self.currency_id.id
            if different_currency
            else journal_currency.id,
            "partner_id": commercial_partner_id.id,
            "payment_method_id": payment_methods and payment_methods[0].id or False,
            "expense_sheet_ids": self.sheet_id.ids,
        }
        return payment_dict

    def action_move_create(self):
        move_sheet_dict = super().action_move_create()
        payment_list = []
        # you can skip create payment from expense paid by company_account
        if self.env.context.get("skip_create_payment_company_account", False):
            return move_sheet_dict
        for expense in self:
            if expense.payment_mode == "company_account":
                total_amount_currency = expense.total_amount
                different_currency = (
                    expense.currency_id != expense.company_id.currency_id
                )
                journal = expense.sheet_id.bank_journal_id
                journal_currency = journal.currency_id or journal.company_id.currency_id
                payment_methods = journal.outbound_payment_method_line_ids.mapped(
                    "payment_method_id"
                )
                # prepare payment dict value for case paid by company
                payment_dict = expense._prepare_payment_expense_company(
                    payment_methods,
                    journal,
                    different_currency,
                    journal_currency,
                    total_amount_currency,
                )
                payment_list.append(payment_dict)
        # create payment and auto post from expense paid by company
        if payment_list:
            payment = self.env["account.payment"].create(payment_list)
            payment.action_post()
        return move_sheet_dict
