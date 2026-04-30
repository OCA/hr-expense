# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase


class TestHrExpensePayToVendor(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_obj = cls.env["res.partner"]
        cls.payment_obj = cls.env["account.payment"]
        cls.journal_obj = cls.env["account.journal"]
        cls.sheet_obj = cls.env["hr.expense.sheet"]
        cls.expense_obj = cls.env["hr.expense"]
        cls.account_payment_register_obj = cls.env["account.payment.register"]

        cls.company = cls.env.ref("base.main_company")
        cls.employee_admin = cls.env.ref("hr.employee_admin")
        cls.product_no_cost = cls.env.ref("hr_expense.product_product_no_cost")

        cls.vendor = cls.partner_obj.create({"name": "Test Vendor"})
        cls.vendor2 = cls.partner_obj.create({"name": "Test Vendor 2"})
        cls.payment_journal = cls.journal_obj.search(
            [
                ("type", "in", ["cash", "bank"]),
                ("company_id", "=", cls.company.id),
            ],
            limit=1,
        )

        cls.expense_journal = cls.journal_obj.create(
            {
                "name": "Purchase Journal - Test",
                "code": "HRTPJ",
                "type": "purchase",
                "company_id": cls.company.id,
            }
        )

    def _get_payment_wizard(self, expense_sheet):
        action = expense_sheet.action_register_payment()
        context = action.get("context", {})
        with Form(
            self.account_payment_register_obj.with_context(**context),
            view="account.view_account_payment_register_form",
        ) as form:
            form.journal_id = self.payment_journal
            form.amount = expense_sheet.total_amount
        return form.save()

    def _create_expense_sheet(self):
        expense_sheet = self.sheet_obj.create(
            {
                "employee_id": self.employee_admin.id,
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expense_obj.create(
            [
                {
                    "name": "Expense Line 1",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product_no_cost.id,
                    "total_amount": 10.0,
                    "sheet_id": expense_sheet.id,
                    "payment_mode": "company_account",
                    "vendor_id": self.vendor.id,
                },
                {
                    "name": "Expense Line 2",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product_no_cost.id,
                    "total_amount": 20.0,
                    "sheet_id": expense_sheet.id,
                    "payment_mode": "company_account",
                    "vendor_id": self.vendor.id,
                },
            ]
        )
        return expense_sheet

    def test_expense_pay_to_vendor(self):
        expense_sheet = self._create_expense_sheet()

        self.assertEqual(expense_sheet.payment_mode, "company_account")
        self.assertEqual(expense_sheet.vendor_id, self.vendor)
        self.assertEqual(
            expense_sheet.expense_line_ids.mapped("vendor_id"), self.vendor
        )

        with self.assertRaises(ValidationError):
            self.expense_obj.create(
                {
                    "name": "Expense Line 3",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product_no_cost.id,
                    "unit_amount": 1.0,
                    "quantity": 10.0,
                    "sheet_id": expense_sheet.id,
                    "payment_mode": "company_account",
                    "vendor_id": self.vendor2.id,
                }
            )

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        expense_move = expense_sheet.account_move_id
        self.assertTrue(expense_move)
        self.assertEqual(
            expense_move.line_ids.filtered(
                lambda line: line.account_id.account_type == "liability_payable"
            ).partner_id,
            self.vendor,
        )

        payment_wizard = self._get_payment_wizard(expense_sheet)
        payment_wizard.action_create_payments()

        reconcile_moves = expense_sheet.account_move_id.line_ids.mapped(
            "full_reconcile_id.reconciled_line_ids.move_id"
        )
        payment_move = reconcile_moves - expense_move

        self.assertTrue(payment_move)
        self.assertEqual(payment_move.partner_id, self.vendor)
        self.assertEqual(
            payment_move.line_ids.filtered(
                lambda line: line.account_id.account_type == "liability_payable"
            ).partner_id,
            self.vendor,
        )
