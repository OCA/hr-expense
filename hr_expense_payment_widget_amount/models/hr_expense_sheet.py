# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json

from odoo import _, api, fields, models
from odoo.tools import date_utils


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    expense_payments_widget = fields.Text(
        compute="_compute_payments_widget_reconciled_info",
        compute_sudo=True,
    )

    def _get_expense_partial_reconciled(self, payment):
        """Find partial reconcile with payment"""
        move_lines = self.account_move_id.line_ids
        partial_reconciled = self.env["account.partial.reconcile"].search(
            [("credit_move_id", "in", move_lines.ids)]
        )
        return partial_reconciled.filtered(
            lambda l: l.debit_move_id.id in payment.move_id.line_ids.ids
        ).ids

    def _get_expense_reconciled_info_JSON_values(self):
        self.ensure_one()
        company_currency = self.env.company.currency_id
        content = []
        # Show only payment reconciled.
        for payment in self.payment_ids.filtered(
            lambda l: l.move_id.line_ids.filtered("reconciled")
        ):
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
                    "partial_id": self._get_expense_partial_reconciled(payment),
                    "payment_id": payment.id,
                    "account_payment_id": payment.id,
                    "payment_method_name": payment.payment_method_id.name
                    if payment.journal_id.type == "bank"
                    else None,
                    "move_id": payment.move_id.id,
                    "ref": payment.ref,
                }
            )
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
