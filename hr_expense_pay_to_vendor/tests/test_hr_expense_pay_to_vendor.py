# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase


class TestHrExpensePayToVendor(TransactionCase):
    def setUp(self):
        super(TestHrExpensePayToVendor, self).setUp()
        self.vendor = self.env["res.partner"].create({"name": "Test Vendor"})
        self.partner1 = self.env.ref("base.res_partner_12")
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

    def _get_payment_wizard(self, expense_sheet):
        ctx = {
            "active_model": "hr.expense.sheet",
            "active_id": self.expense_sheet.id,
            "active_ids": [self.expense_sheet.id],
            "default_amount": self.expense_sheet.total_amount,
            "partner_id": self.expense_sheet.address_id.id,
        }
        with Form(
            self.env["hr.expense.sheet.register.payment.wizard"].with_context(ctx)
        ) as f:
            f.journal_id = self.payment_journal
        wizard = f.save()
        wizard.expense_post_payment()

    def test_expense_pay_to_vendor(self):
        """When expense is set to pay to vendor, I expect,
        - After post journal entries, all journal items will use partner_id = vendor
        - After make payment, all journal items will use partner_id = vendor
        """
        self.expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "employee_id": self.ref("hr.employee_admin"),
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expenses = self.env["hr.expense"].create(
            [
                {
                    "name": "Expense Line 1",
                    "employee_id": self.ref("hr.employee_admin"),
                    "product_id": self.ref("hr_expense.air_ticket"),
                    "unit_amount": 1,
                    "quantity": 10,
                    "sheet_id": self.expense_sheet.id,
                    "payment_mode": "company_account",
                    "vendor_id": self.vendor.id,
                },
                {
                    "name": "Expense Line 1",
                    "employee_id": self.ref("hr.employee_admin"),
                    "product_id": self.ref("hr_expense.air_ticket"),
                    "unit_amount": 1,
                    "quantity": 20,
                    "sheet_id": self.expense_sheet.id,
                    "payment_mode": "company_account",
                    "vendor_id": self.partner1.id,
                },
            ]
        )
        # Test pay to multi vendor, it error
        with self.assertRaises(ValidationError):
            self.expense_sheet._check_payment_mode()
        # Change vendor to Test Vendor
        self.expenses[1].vendor_id = self.vendor.id
        self.assertEqual(self.expense_sheet.payment_mode, "company_account")
        self.assertEqual(
            list(set(self.expense_sheet.expense_line_ids.mapped("payment_mode"))),
            ["company_account"],
        )
        # Post Journl Entry
        self.expense_sheet.action_submit_sheet()
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        expense_move = self.expense_sheet.account_move_id
        vendor_name = expense_move.line_ids.mapped("partner_id.name")[0]
        self.assertEqual(vendor_name, "Test Vendor")
        # Make payment
        self._get_payment_wizard(self.expense_sheet)
        # Payment move, should also use partner_id = vendor
        reconcile_moves = self.expense_sheet.account_move_id.line_ids.mapped(
            "full_reconcile_id.reconciled_line_ids.move_id"
        )
        payment_move = reconcile_moves - expense_move
        vendor_name = payment_move.line_ids.mapped("partner_id.name")[0]
        self.assertEqual(vendor_name, "Test Vendor")
