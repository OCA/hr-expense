# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import Form, TransactionCase


class TestHrExpenseCancel(TransactionCase):
    def setUp(self):
        super().setUp()
        self.partner = self.env["res.partner"].create({"name": "Test partner"})
        self.payment_obj = self.env["account.payment"]
        self.account_payment_register = self.env["account.payment.register"]
        self.payment_journal = self.env["account.journal"].search(
            [("type", "in", ["cash", "bank"])], limit=1
        )

        self.main_company = company = self.env.ref("base.main_company")
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
                "product_id": self.ref("hr_expense.trans_expense_product"),
                "unit_amount": 1,
                "quantity": 10,
                "sheet_id": self.expense_sheet.id,
            }
        )

        self.expense_sheet2 = self.env["hr.expense.sheet"].create(
            {
                "employee_id": self.ref("hr.employee_admin"),
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expense_sheet2.approve_expense_sheets()

        self.expense2 = self.env["hr.expense"].create(
            {
                "name": "Expense test",
                "employee_id": self.ref("hr.employee_admin"),
                "product_id": self.ref("hr_expense.trans_expense_product"),
                "unit_amount": 2,
                "quantity": 10,
                "sheet_id": self.expense_sheet2.id,
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

    def test_action_cancel_posted(self):
        self.expense_sheet.action_sheet_move_create()

        self.assertFalse(len(self.expense_sheet.payment_ids), 1)
        self.assertTrue(self.expense_sheet.account_move_id)

        self.expense_sheet.action_cancel()

        self.assertFalse(self.expense_sheet.payment_ids)
        self.assertFalse(self.expense_sheet.account_move_id)

    def test_action_cancel_no_update_posted(self):
        journals = self.payment_journal | self.expense_journal
        journals.write({"restrict_mode_hash_table": True})
        self.test_action_cancel_company_account()
        with self.assertRaises(UserError):
            self.test_action_cancel_own_account()

    def test_action_cancel_company_account(self):
        self.expense.payment_mode = "company_account"
        self.expense_sheet.action_sheet_move_create()

        self.assertEqual(len(self.expense_sheet.payment_ids), 1)
        self.assertTrue(self.expense_sheet.account_move_id)

        self.expense_sheet.action_cancel()
        payment = self.expense_sheet.payment_ids.filtered(lambda l: l.state != "cancel")
        self.assertFalse(payment)
        self.assertFalse(self.expense_sheet.account_move_id)

    def test_action_cancel_own_account(self):
        self.expense_sheet.action_sheet_move_create()

        payment_wizard = self._get_payment_wizard(self.expense_sheet)
        payment_wizard.action_create_payments()

        self.assertEqual(len(self.expense_sheet.payment_ids), 1)
        self.assertTrue(self.expense_sheet.account_move_id)

        self.expense_sheet.action_cancel()
        payment = self.expense_sheet.payment_ids.filtered(lambda l: l.state != "cancel")
        self.assertFalse(payment)
        self.assertFalse(self.expense_sheet.account_move_id)

    def test_action_cancel_multi_own_account(self):
        self.expense_sheet.action_sheet_move_create()
        self.expense_sheet2.action_sheet_move_create()
        expense_sheet_ids = self.expense_sheet + self.expense_sheet2
        payment_wizard = self._get_payment_wizard(expense_sheet_ids)
        payment_wizard.action_create_payments()

        self.assertEqual(len(self.expense_sheet.payment_ids), 1)
        self.assertTrue(self.expense_sheet.account_move_id)

        self.expense_sheet.action_cancel()
        payment = self.expense_sheet.payment_ids.filtered(lambda l: l.state != "cancel")
        self.assertFalse(payment)
        self.assertFalse(self.expense_sheet.account_move_id)
