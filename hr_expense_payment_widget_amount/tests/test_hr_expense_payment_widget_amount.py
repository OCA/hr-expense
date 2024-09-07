# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestHrExpensePaymentWidgetAmount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.journal_obj = cls.env["account.journal"]
        cls.sheet_obj = cls.env["hr.expense.sheet"]
        cls.expense_obj = cls.env["hr.expense"]
        cls.account_payment_register_obj = cls.env["account.payment.register"]

        cls.expense_product = cls.env.ref("hr_expense.expense_product_meal")
        cls.employee = cls.env.ref("hr.employee_admin")
        cls.currency_usd_id = cls.env.ref("base.USD").id
        cls.currency_eur_id = cls.env.ref("base.EUR").id
        cls.company = cls.env.ref("base.main_company")

        # Set company currency to USD
        cls.env.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            [cls.currency_usd_id, cls.company.id],
        )

        cls.payment_journal = cls.journal_obj.search(
            [("type", "in", ["cash", "bank"])], limit=1
        )
        cls.expense_journal = cls.journal_obj.create(
            {
                "name": "Purchase Journal - Test",
                "code": "HRTPJ",
                "type": "purchase",
                "company_id": cls.company.id,
            }
        )

        cls.expense_sheet = cls.sheet_obj.create(
            {
                "employee_id": cls.employee.id,
                "name": "Expense test",
                "journal_id": cls.expense_journal.id,
            }
        )
        cls.expense_sheet.approve_expense_sheets()

        cls.expense = cls.expense_obj.create(
            {
                "name": "Expense test",
                "employee_id": cls.employee.id,
                "product_id": cls.expense_product.id,
                "total_amount": 10,
                "sheet_id": cls.expense_sheet.id,
            }
        )

        cls.expense_sheet_currency = cls.sheet_obj.create(
            {
                "employee_id": cls.employee.id,
                "name": "Expense test",
                "journal_id": cls.expense_journal.id,
            }
        )
        cls.expense_sheet_currency.approve_expense_sheets()

        cls.expense_currency = cls.expense_obj.create(
            {
                "name": "Expense test",
                "employee_id": cls.employee.id,
                "product_id": cls.expense_product.id,
                "total_amount": 10,
                "currency_id": cls.currency_eur_id,
                "sheet_id": cls.expense_sheet_currency.id,
            }
        )

    def _get_payment_wizard(self, expense_sheet):
        action = expense_sheet.action_register_payment()
        ctx = action.get("context")
        with Form(
            self.account_payment_register_obj.with_context(**ctx),
            view="account.view_account_payment_register_form",
        ) as f:
            f.journal_id = self.payment_journal
            f.amount = expense_sheet.total_amount
        register_payment = f.save()
        return register_payment

    def test_01_expense_sheet_employee(self):
        # Post Journal Entries
        self.expense_sheet.action_sheet_move_create()
        self.assertEqual(self.expense_sheet.state, "post")
        payment_wizard = self._get_payment_wizard(self.expense_sheet)
        payment_widget = self.expense_sheet.expense_payments_widget
        self.assertFalse(self.expense_sheet.payment_ids)
        self.assertFalse(payment_widget)
        # Register Payment
        payment_wizard.action_create_payments()
        self.assertEqual(len(self.expense_sheet.payment_ids), 1)

        payment_widget = self.expense_sheet.expense_payments_widget
        self.assertTrue(payment_widget)
        content_payment_widget = payment_widget.get("content", False)
        self.assertEqual(len(content_payment_widget), 1)
        # Unreconciled widget from expense sheet view
        move = self.expense_sheet.payment_ids.move_id
        self.assertEqual(move.id, content_payment_widget[0].get("move_id"))
        # when click on unreconciled button from expense sheet,
        # it will send id from move but object is hr.expense.sheet
        x = self.sheet_obj.browse(move.id)
        x.js_remove_outstanding_partial(content_payment_widget[0].get("partial_id"))
        payment_widget = self.expense_sheet.expense_payments_widget
        self.assertFalse(payment_widget)

    def test_02_expense_sheet_employee_currency(self):
        """
        Expense with currency EUR, Company currency USD.
        It will convert EUR -> USD display on expense sheet.
        """
        self.expense_sheet_currency.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard(self.expense_sheet_currency)
        payment_widget = self.expense_sheet_currency.expense_payments_widget
        self.assertFalse(self.expense_sheet_currency.payment_ids)
        self.assertFalse(payment_widget)
        payment_wizard.action_create_payments()
        self.assertEqual(len(self.expense_sheet_currency.payment_ids), 1)
        payment_widget = self.expense_sheet_currency.expense_payments_widget
        self.assertTrue(payment_widget)
        content_payment_widget = payment_widget.get("content", False)
        self.assertEqual(len(content_payment_widget), 1)
        self.assertTrue(self.expense_sheet_currency.expense_payments_widget)
        # widget amount display will show amount currency
        self.assertEqual(
            round(content_payment_widget[0]["amount"], 2),
            self.expense_sheet_currency.total_amount,
        )
