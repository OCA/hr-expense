# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json

from odoo.tests.common import Form, TransactionCase


class TestHrExpensePaymentWidgetAmount(TransactionCase):
    def setUp(self):
        super().setUp()
        self.account_payment_register = self.env["account.payment.register"]
        self.payment_journal = self.env["account.journal"].search(
            [("type", "in", ["cash", "bank"])], limit=1
        )
        company = self.env.ref("base.main_company")
        self.currency_usd_id = self.env.ref("base.USD").id
        self.currency_eur_id = self.env.ref("base.EUR").id
        self.env.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            [self.currency_usd_id, company.id],
        )
        company.invalidate_cache()

        self.expense_journal = self.env["account.journal"].create(
            {
                "name": "Purchase Journal - Test",
                "code": "HRTPJ",
                "type": "purchase",
                "company_id": company.id,
            }
        )

        self.expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "employee_id": self.ref("hr.employee_admin"),
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expense_sheet.approve_expense_sheets()

        self.expense = self.env["hr.expense"].create(
            {
                "name": "Expense test",
                "employee_id": self.ref("hr.employee_admin"),
                "product_id": self.ref("hr_expense.accomodation_expense_product"),
                "unit_amount": 1,
                "quantity": 10,
                "sheet_id": self.expense_sheet.id,
            }
        )

        self.expense_sheet_currency = self.env["hr.expense.sheet"].create(
            {
                "employee_id": self.ref("hr.employee_admin"),
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expense_sheet_currency.approve_expense_sheets()

        self.expense_currency = self.env["hr.expense"].create(
            {
                "name": "Expense test",
                "employee_id": self.ref("hr.employee_admin"),
                "product_id": self.ref("hr_expense.accomodation_expense_product"),
                "unit_amount": 1,
                "quantity": 10,
                "currency_id": self.currency_eur_id,
                "sheet_id": self.expense_sheet_currency.id,
            }
        )

    def _get_payment_wizard(self, expense_sheet):
        action = expense_sheet.action_register_payment()
        ctx = action.get("context")
        with Form(
            self.account_payment_register.with_context(**ctx),
            view="account.view_account_payment_register_form",
        ) as f:
            f.journal_id = self.payment_journal
            f.amount = self.expense_sheet.total_amount
        register_payment = f.save()
        return register_payment

    def test_01_expense_sheet_employee(self):
        # Post Journal Entries
        self.expense_sheet.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard(self.expense_sheet)
        payment_widget = json.loads(self.expense_sheet.expense_payments_widget)
        self.assertFalse(self.expense_sheet.payment_ids)
        self.assertFalse(payment_widget)
        # Register Payment
        payment_wizard.action_create_payments()
        self.assertEqual(len(self.expense_sheet.payment_ids), 1)
        payment_widget = json.loads(self.expense_sheet.expense_payments_widget)
        self.assertTrue(payment_widget)
        content_payment_widget = payment_widget.get("content", False)
        self.assertEqual(len(content_payment_widget), 1)
        # Unreconciled widget
        move = self.expense_sheet.payment_ids.move_id
        self.assertEqual(move.id, content_payment_widget[0].get("move_id"))
        move.js_remove_outstanding_partial(content_payment_widget[0].get("partial_id"))
        payment_widget = json.loads(self.expense_sheet.expense_payments_widget)
        self.assertFalse(payment_widget.get("content"))

    def test_02_expense_sheet_employee_currency(self):
        """
        Expense with currency EUR, Company currency USD.
        It will convert EUR -> USD display on expense sheet.
        """
        self.expense_sheet_currency.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard(self.expense_sheet_currency)
        payment_widget = json.loads(self.expense_sheet_currency.expense_payments_widget)
        self.assertFalse(self.expense_sheet_currency.payment_ids)
        self.assertFalse(payment_widget)
        payment_wizard.action_create_payments()
        self.assertEqual(len(self.expense_sheet_currency.payment_ids), 1)
        payment_widget = json.loads(self.expense_sheet_currency.expense_payments_widget)
        self.assertTrue(payment_widget)
        content_payment_widget = payment_widget.get("content", False)
        self.assertEqual(len(content_payment_widget), 1)
        self.assertTrue(self.expense_sheet_currency.expense_payments_widget)
        # widget amount display will show amount currency
        self.assertEqual(
            round(content_payment_widget[0]["amount"], 2),
            self.expense_sheet_currency.total_amount,
        )
