# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models
from odoo.tools import date_utils


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    expense_payments_widget = fields.Text(
        compute="_compute_payments_widget_reconciled_info",
        groups="account.group_account_invoice,account.group_account_readonly",
    )

    def _get_expense_reconciled_info_JSON_values(self):
        self.ensure_one()
        company_currency = self.env.company.currency_id
        content = self.account_move_id._get_reconciled_info_JSON_values()
        # Paid by company can't reconciled because there is not account move.
        if self.account_move_id.journal_id == self.bank_journal_id:
            for payment in self.payment_ids:
                amount_currency = payment.currency_id._convert(
                    payment.amount, company_currency, self.company_id, payment.date
                )
                content.append(
                    {
                        "name": payment.name,
                        "journal_name": payment.journal_id.name,
                        "amount": amount_currency,
                        "currency": self.currency_id.symbol,
                        "digits": [69, self.currency_id.decimal_places],
                        "position": self.currency_id.position,
                        "date": payment.date,
                        "payment_id": payment.id,
                        "account_payment_id": payment.id,
                        "payment_method_name": payment.payment_method_id.name
                        if payment.journal_id.type == "bank"
                        else None,
                        "move_id": payment.move_id.id,
                        "ref": payment.ref,
                    }
                )
        elif self.account_move_id.journal_id == self.journal_id:
            for partial in self.account_move_id._get_reconciled_invoices_partials():
                list_content = list(
                    filter(
                        lambda content: content["partial_id"] == partial[0].id, content
                    )
                )
                # expense sheet display with company currency only BUT
                # function _get_reconciled_invoices_partials() will get amount from
                # currency paid, it should be display widget by company currency.
                list_content[0]["amount"] = partial[0].amount
        return content

    @api.depends("payment_ids")
    def _compute_payments_widget_reconciled_info(self):
        payments_widget_vals = {
            "title": _("Less Payment"),
            "outstanding": False,
            "content": [],
        }
        for rec in self:
            rec.expense_payments_widget = json.dumps(False)
            if rec.payment_ids:
                payments_widget_vals[
                    "content"
                ] = rec._get_expense_reconciled_info_JSON_values()
                rec.expense_payments_widget = json.dumps(
                    payments_widget_vals, default=date_utils.json_default
                )
