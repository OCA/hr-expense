# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase

from ..hooks import post_init_hook


class TestHrExpensePayment(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_payment_register = cls.env["account.payment.register"]
        cls.payment_journal = cls.env["account.journal"].search(
            [("type", "in", ["cash", "bank"])], limit=1
        )

        company = cls.env.ref("base.main_company")
        cls.expense_journal = cls.env["account.journal"].create(
            {
                "name": "Purchase Journal - Test",
                "code": "HRTPJ",
                "type": "purchase",
                "company_id": company.id,
            }
        )

        cls.expense_sheet = cls.env["hr.expense.sheet"].create(
            {
                "employee_id": cls.env.ref("hr.employee_admin").id,
                "name": "Expense test",
                "journal_id": cls.expense_journal.id,
            }
        )
        cls.expense_sheet.action_approve_expense_sheets()

        cls.expense = cls.env["hr.expense"].create(
            {
                "name": "Expense test",
                "employee_id": cls.env.ref("hr.employee_admin").id,
                "product_id": cls.env.ref("hr_expense.expense_product_meal").id,
                "total_amount": 1000,
                "sheet_id": cls.expense_sheet.id,
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

    def test_post_init_hook(self):
        self.expense_sheet.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard(self.expense_sheet)
        payment_wizard.action_create_payments()

        payment = self.expense_sheet.payment_ids

        self.assertEqual(len(payment), 1)
        self.assertEqual(len(payment.expense_sheet_ids), 1)

        payment.expense_sheet_ids = False
        # Recompute many2one
        payment = self.expense_sheet.payment_ids

        self.assertFalse(payment)
        self.assertFalse(payment.expense_sheet_ids)
        post_init_hook(self.env)

        self.assertEqual(len(self.expense_sheet.payment_ids), 1)

    def test_get_payment_vals(self):
        self.expense_sheet.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard(self.expense_sheet)
        self.assertFalse(self.expense_sheet.payment_ids)
        payment_wizard.action_create_payments()
        self.assertEqual(len(self.expense_sheet.payment_ids), 1)
