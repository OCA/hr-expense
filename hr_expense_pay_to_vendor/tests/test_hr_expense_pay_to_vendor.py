# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
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

        cls.main_company = company = cls.env.ref("base.main_company")
        cls.employee_admin = cls.env.ref("hr.employee_admin")
        cls.product_no_cost = cls.env.ref("hr_expense.product_product_no_cost")

        cls.vendor = cls.partner_obj.create({"name": "Test Vendor"})
        cls.vendor2 = cls.partner_obj.create({"name": "Test Vendor2"})
        cls.payment_journal = cls.journal_obj.search(
            [("type", "in", ["cash", "bank"])], limit=1
        )

        cls.expense_journal = cls.journal_obj.create(
            {
                "name": "Purchase Journal - Test",
                "code": "HRTPJ",
                "type": "purchase",
                "company_id": company.id,
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
            f.amount = self.expense_sheet.total_amount
        register_payment = f.save()
        return register_payment

    def test_expense_pay_to_vendor(self):
        """When expense is set to pay to vendor, I expect,
        - After post journal entries, all journal items will use partner_id = vendor
        - After make payment, all journal items will use partner_id = vendor
        """
        self.expense_sheet = self.sheet_obj.create(
            {
                "employee_id": self.employee_admin.id,
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expenses = self.expense_obj.create(
            [
                {
                    "name": "Expense Line 1",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product_no_cost.id,
                    "total_amount": 10,
                    "sheet_id": self.expense_sheet.id,
                    "payment_mode": "company_account",
                    "vendor_id": self.vendor.id,
                },
                {
                    "name": "Expense Line 1",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product_no_cost.id,
                    "total_amount": 20,
                    "sheet_id": self.expense_sheet.id,
                    "payment_mode": "company_account",
                    "vendor_id": self.vendor.id,
                },
            ]
        )
        self.assertEqual(self.expense_sheet.payment_mode, "company_account")
        self.assertEqual(
            list(set(self.expense_sheet.expense_line_ids.mapped("payment_mode"))),
            ["company_account"],
        )
        # Test create new expense diff vendor
        with self.assertRaises(UserError):
            self.expense_obj.create(
                [
                    {
                        "name": "Expense Line 1",
                        "employee_id": self.employee_admin.id,
                        "product_id": self.product_no_cost.id,
                        "unit_amount": 1,
                        "quantity": 10,
                        "sheet_id": self.expense_sheet.id,
                        "payment_mode": "company_account",
                        "vendor_id": self.vendor2.id,
                    },
                ]
            )
        # Post Journl Entry
        self.expense_sheet.action_submit_sheet()
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        expense_move = self.expense_sheet.account_move_id
        vendor_name = expense_move.line_ids.mapped("partner_id.name")[0]
        self.assertEqual(vendor_name, "Test Vendor")
        # Make payment
        payment_wizard = self._get_payment_wizard(self.expense_sheet)
        payment_wizard.action_create_payments()
        # Payment move, should also use partner_id = vendor
        reconcile_moves = self.expense_sheet.account_move_id.line_ids.mapped(
            "full_reconcile_id.reconciled_line_ids.move_id"
        )
        payment_move = reconcile_moves - expense_move
        vendor_name = payment_move.line_ids.mapped("partner_id.name")[0]
        self.assertEqual(vendor_name, "Test Vendor")
