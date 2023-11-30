# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase

from ..hooks import post_init_hook


class TestHrExpensePayment(TransactionCase):
    def setUp(self):
        super().setUp()
        self.account_payment_register = self.env["account.payment.register"]
        self.payment_journal = self.env["account.journal"].search(
            [("type", "in", ["cash", "bank"])], limit=1
        )

        company = self.env.ref("base.main_company")
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
                "product_id": self.ref("hr_expense.expense_product_meal"),
                "total_amount": 1000,
                "sheet_id": self.expense_sheet.id,
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
        post_init_hook(self.env.cr, self.registry)

        self.assertEqual(len(self.expense_sheet.payment_ids), 1)

    def test_get_payment_vals(self):
        self.expense_sheet.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard(self.expense_sheet)
        self.assertFalse(self.expense_sheet.payment_ids)
        payment_wizard.action_create_payments()
        self.assertEqual(len(self.expense_sheet.payment_ids), 1)
