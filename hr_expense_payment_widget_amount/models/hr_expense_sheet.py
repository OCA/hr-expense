# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.tools.misc import formatLang


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    expense_payments_widget = fields.Binary(
        compute="_compute_payments_widget_reconciled_info",
        exportable=False,
    )

    def action_open_business_doc(self):
        """
        This method searches for the payment related
        to the expense sheet and opens it in a new form view.
        """
        self.ensure_one()
        # NOTE: when opening the payment from the expense sheet,
        # 'self' use the 'hr.expense.sheet' model but id is move_id,
        # so we need to search for the payment
        payment = self.env["account.payment"].search([("move_id", "=", self.id)])
        return {
            "name": _("Payment"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "views": [(False, "form")],
            "res_model": "account.payment",
            "res_id": payment.id,
            "target": "current",
        }

    def _get_expense_partial_reconciled(self, payment):
        """Find partial reconcile with payment"""
        credit_mls = self.account_move_id.line_ids
        debit_mls = payment.move_id.line_ids
        query = """
            SELECT id FROM account_partial_reconcile
            WHERE credit_move_id IN %s AND debit_move_id IN %s
        """
        self.env.cr.execute(query, (tuple(credit_mls.ids), tuple(debit_mls.ids)))
        partial_reconciled_ids = [x[0] for x in self.env.cr.fetchall()]
        return partial_reconciled_ids

    @api.depends("payment_ids")
    def _compute_payments_widget_reconciled_info(self):
        company_currency = self.env.company.currency_id
        for rec in self:
            payments_widget_vals = {
                "title": _("Less Payment"),
                "outstanding": False,
                "content": [],
            }

            if rec.payment_ids:
                reconciled_vals = []
                # Show only payment reconciled.
                for payment in rec.payment_ids.filtered(
                    lambda l: l.move_id.line_ids.filtered("reconciled")
                ):
                    amount_currency = payment.currency_id._convert(
                        payment.amount, company_currency, rec.company_id, payment.date
                    )
                    reconciled_vals.append(
                        {
                            "name": payment.name,
                            "journal_name": payment.journal_id.name,
                            "amount": amount_currency,
                            "currency_id": rec.currency_id.id,
                            "date": payment.date,
                            "partial_id": rec._get_expense_partial_reconciled(payment)[
                                0
                            ],
                            "account_payment_id": payment.id,
                            "payment_method_name": payment.payment_method_id.name
                            if payment.journal_id.type == "bank"
                            else None,
                            "move_id": payment.move_id.id,
                            "ref": payment.ref,
                            "amount_company_currency": formatLang(
                                self.env,
                                abs(payment.amount_company_currency_signed),
                                currency_obj=payment.company_id.currency_id,
                            ),
                            "amount_foreign_currency": formatLang(
                                self.env,
                                abs(payment.amount),
                                currency_obj=payment.currency_id,
                            ),
                        }
                    )
                payments_widget_vals["content"] = reconciled_vals

            if payments_widget_vals["content"]:
                rec.expense_payments_widget = payments_widget_vals
            else:
                rec.expense_payments_widget = False

    def js_remove_outstanding_partial(self, partial_id):
        """Expense Report can partial reconcile with multi line.
        So, this function will check all partial reconcile for multi unreconciled partial"""
        self.ensure_one()
        # NOTE: when unreconcile the payment from the expense sheet,
        # 'self' use the 'hr.expense.sheet' model but id is move_id,
        # so we need to search for the move
        move = self.env["account.move"].browse(self.id)
        partial = self.env["account.partial.reconcile"].search(
            [("debit_move_id", "in", move.line_ids.ids)]
        )
        return partial.unlink()
