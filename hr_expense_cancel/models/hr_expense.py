# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def _create_hook_payment(
        self,
        payment_methods,
        total_amount,
        journal,
        different_currency,
        journal_currency,
        total_amount_currency,
    ):
        self.ensure_one()
        commercial_partner_id = (
            self.employee_id.sudo().address_home_id.commercial_partner_id
        )
        payment = self.env["account.payment"].create(
            {
                "payment_method_id": payment_methods and payment_methods[0].id or False,
                "payment_type": "outbound" if total_amount < 0 else "inbound",
                "partner_id": commercial_partner_id.id,
                "partner_type": "supplier",
                "journal_id": journal.id,
                "date": self.date,
                "currency_id": self.currency_id.id
                if different_currency
                else journal_currency.id,
                "amount": abs(total_amount_currency)
                if different_currency
                else abs(total_amount),
                "ref": self.name,
                "expense_sheet_id": self.sheet_id.id,
            }
        )
        return payment

    def action_move_create(self):
        """ Overwrite main function for update value payment """
        move_group_by_sheet = self._get_account_move_by_sheet()

        move_line_values_by_expense = self._get_account_move_line_values()

        for expense in self:
            company_currency = expense.company_id.currency_id
            different_currency = expense.currency_id != company_currency

            # get the account move of the related sheet
            move = move_group_by_sheet[expense.sheet_id.id]

            # get move line values
            move_line_values = move_line_values_by_expense.get(expense.id)
            move_line_dst = move_line_values[-1]
            total_amount = move_line_dst["debit"] or -move_line_dst["credit"]
            total_amount_currency = move_line_dst["amount_currency"]

            # create one more move line, a counterline for the total on payable account
            if expense.payment_mode == "company_account":
                if not expense.sheet_id.bank_journal_id.default_account_id:
                    raise UserError(
                        _("No account found for the %s journal, please configure one.")
                        % (expense.sheet_id.bank_journal_id.name)
                    )
                journal = expense.sheet_id.bank_journal_id
                # create payment
                payment_methods = (
                    journal.outbound_payment_method_ids
                    if total_amount < 0
                    else journal.inbound_payment_method_ids
                )
                journal_currency = journal.currency_id or journal.company_id.currency_id
                payment = expense._create_hook_payment(
                    payment_methods,
                    total_amount,
                    journal,
                    different_currency,
                    journal_currency,
                    total_amount_currency,
                )
                move_line_dst["payment_id"] = payment.id

            # link move lines to move, and move to expense sheet
            move.write({"line_ids": [(0, 0, line) for line in move_line_values]})
            expense.sheet_id.write({"account_move_id": move.id})

            if expense.payment_mode == "company_account":
                expense.sheet_id.paid_expense_sheets()

        # post the moves
        for move in move_group_by_sheet.values():
            move._post()

        return move_group_by_sheet


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_cancel(self):
        for sheet in self:
            account_move = sheet.account_move_id
            sheet.account_move_id = False
            payments = self.env["account.payment"].search(
                [("expense_sheet_id", "=", sheet.id), ("state", "!=", "cancel")]
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
            rec.move_id.button_cancel()

    def action_register_payment(self):
        action = super().action_register_payment()
        if self._name == "hr.expense.sheet":
            action["context"].update({"expense_sheet_ids": self.ids})
        return action
