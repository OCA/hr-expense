# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestHrExpenseTaxAdjust(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense = cls.env["hr.expense"]
        cls.sheet = cls.env["hr.expense.sheet"]
        cls.employee_admin = cls.env.ref("hr.employee_admin")
        cls.expense_product = cls.env.ref("hr_expense.trans_expense_product")
        cls.tax_purchase_include = cls.env["account.tax"].create(
            {
                "name": "Test tax 10% (include)",
                "type_tax_use": "purchase",
                "amount": 10.00,
                "price_include": True,
            }
        )
        cls.tax_purchase = cls.env["account.tax"].create(
            {
                "name": "Test tax 10%",
                "type_tax_use": "purchase",
                "amount": 10.00,
            }
        )

    def test_01_expense_adjust_tax_include_tax(self):
        expense = self.expense.create(
            {
                "name": "Expense test",
                "employee_id": self.employee_admin.id,
                "product_id": self.expense_product.id,
                "unit_amount": 10,
                "quantity": 10,
                "tax_ids": [(6, 0, [self.tax_purchase_include.id])],
            }
        )
        self.assertEqual(expense.total_amount, 100)
        self.assertFalse(expense.tax_adjust)
        self.assertEqual(expense.price_tax, 9.09)  # (100 * 10) / 110
        # Test increase taxes adjust
        with Form(expense) as ex:
            ex.price_tax = 10.0
        self.assertTrue(expense.tax_adjust)
        self.assertEqual(expense.price_tax, 10.0)
        # Create expense sheet
        sheet = self.sheet.create(
            {
                "employee_id": self.employee_admin.id,
                "name": "Expense test",
                "expense_line_ids": [(6, 0, expense.id)],
            }
        )
        self.assertEqual(sheet.state, "draft")
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertTrue(sheet.account_move_id)
        self.assertEqual(len(sheet.account_move_id.line_ids), 3)
        sheet.expense_line_ids._get_expense_account_source()
        src_move_line = sheet.account_move_id.line_ids[0]
        tax_move_line = sheet.account_move_id.line_ids[1]
        # Before adjust tax, source move line must accounting debit = 90.91
        # After adjust tax, it change accounting debit = 90 and tax debit = 10
        self.assertEqual(src_move_line.debit, 90.0)
        self.assertEqual(tax_move_line.debit, 10.0)

        sheet.action_unpost()
        # Test increase taxes adjust
        with Form(expense) as ex:
            ex.price_tax = 8
        self.assertTrue(expense.tax_adjust)
        self.assertEqual(expense.price_tax, 8.0)
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        src_move_line = sheet.account_move_id.line_ids[0]
        tax_move_line = sheet.account_move_id.line_ids[1]
        # Before adjust tax, source move line must accounting debit = 90.91
        # After adjust tax, it change accounting debit = 92 and tax debit = 8
        self.assertEqual(src_move_line.debit, 92.0)
        self.assertEqual(tax_move_line.debit, 8.0)

    def test_02_expense_adjust_tax_exclude_tax(self):
        """In the core Odoo implementation, Tax exclude is invisible.
        This test supports tax exclude if you develop it see it."""
        expense = self.expense.create(
            {
                "name": "Expense test",
                "employee_id": self.employee_admin.id,
                "product_id": self.expense_product.id,
                "unit_amount": 10,
                "quantity": 10,
                "tax_ids": [(6, 0, [self.tax_purchase.id])],
            }
        )
        self.assertEqual(expense.total_amount, 110)
        self.assertFalse(expense.tax_adjust)
        self.assertEqual(expense.price_tax, 10)
        # Test increase taxes adjust
        with Form(expense) as ex:
            ex.price_tax = 12.0
        self.assertTrue(expense.tax_adjust)
        self.assertEqual(expense.price_tax, 12.0)
        # Create expense sheet
        sheet = self.sheet.create(
            {
                "employee_id": self.employee_admin.id,
                "name": "Expense test",
                "expense_line_ids": [(6, 0, expense.id)],
            }
        )
        self.assertEqual(sheet.state, "draft")
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertTrue(sheet.account_move_id)
        self.assertEqual(len(sheet.account_move_id.line_ids), 3)
        sheet.expense_line_ids._get_expense_account_source()
        tax_move_line = sheet.account_move_id.line_ids[1]
        dest_move_line = sheet.account_move_id.line_ids[2]
        # Before adjust tax, dest move line must accounting credit = 110
        # After adjust tax, it change accounting credit = 112 and tax debit = 12
        self.assertEqual(tax_move_line.debit, 12.0)
        self.assertEqual(dest_move_line.credit, 112.0)

        sheet.action_unpost()
        # Test increase taxes adjust
        with Form(expense) as ex:
            ex.price_tax = 8
        self.assertTrue(expense.tax_adjust)
        self.assertEqual(expense.price_tax, 8.0)
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        tax_move_line = sheet.account_move_id.line_ids[1]
        dest_move_line = sheet.account_move_id.line_ids[2]
        # Before adjust tax, source move line must accounting credit = 110
        # After adjust tax, it change accounting credit = 108 and tax debit = 8
        self.assertEqual(tax_move_line.debit, 8.0)
        self.assertEqual(dest_move_line.credit, 108.0)
