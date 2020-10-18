# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_cancel(self):
        for sheet in self:
            account_move = sheet.account_move_id
            sheet.account_move_id = False
            payments = self.env["account.payment"].search(
                [("expense_sheet_id", "=", sheet.id), ("state", "!=", "cancelled")]
            )
            # case : cancel invoice from hr_expense
            self._remove_reconcile_hr_invoice(account_move)
            # If the sheet is paid then remove payments
            if sheet.state == "done":
                if sheet.expense_line_ids[:1].payment_mode == "own_account":
                    self._remove_move_reconcile(payments, account_move)
                    self._cancel_payments(payments)
                else:
                    # In this case, during the cancellation the journal entry
                    # will be deleted
                    self._cancel_payments(payments)
            # Deleting the Journal entry if in the previous steps
            # (if the expense sheet is paid and payment_mode == 'own_account')
            # it has not been deleted
            if account_move.exists():
                if account_move.state != "draft":
                    account_move.button_cancel()
                account_move.with_context({"force_delete": True}).unlink()
            sheet.state = "submit"

    def action_sheet_move_create(self):
        res = super().action_sheet_move_create()
        payment = self.env["account.payment"].search([], order="id desc", limit=1)
        if self.expense_line_ids[0].payment_mode == "company_account":
            payment.write({"expense_sheet_id": self.id})
        return res

    def _remove_reconcile_hr_invoice(self, account_move):
        """Cancel invoice made by hr_expense_invoice module automatically"""
        reconcile = account_move.mapped("line_ids.full_reconcile_id")
        aml = self.env["account.move.line"].search(
            [("full_reconcile_id", "in", reconcile.ids)]
        )
        exp_move_line = aml.filtered(lambda l: l.move_id.id != account_move.id)
        # set state to cancel
        exp_move_line.move_id.button_draft()
        exp_move_line.move_id.button_cancel()

    def _remove_move_reconcile(self, payments, account_move):
        """Delete only reconciliations made with the payments generated
        by hr_expense module automatically"""
        reconcile = account_move.mapped("line_ids.full_reconcile_id")
        payments_aml = payments.move_id.line_ids
        aml_unreconcile = payments_aml.filtered(
            lambda r: r.full_reconcile_id in reconcile
        )

        aml_unreconcile.remove_move_reconcile()

    def _cancel_payments(self, payments):
        for rec in payments:
            rec.move_id.with_context({"force_delete": True}).unlink()

    def action_register_payment(self):
        action = super().action_register_payment()
        if self._name == "hr.expense.sheet":
            action["context"].update({"expense_sheet_ids": self.ids})
        return action
