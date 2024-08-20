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
        cls.expense_product = cls.env.ref("hr_expense.expense_product_meal")
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.usd_currency = cls.env.ref("base.USD")
        cls.company = cls.env.ref("base.main_company")
        cls.company.currency_id = cls.usd_currency

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
                "total_amount": 100.0,
                "tax_ids": [(6, 0, [self.tax_purchase_include.id])],
            }
        )
        self.assertEqual(expense.total_amount, 100)
        self.assertFalse(expense.tax_adjust)
        self.assertEqual(expense.amount_tax, 9.09)  # (100 * 10) / 110
        # Test increase taxes adjust
        with Form(expense) as ex:
            ex.tax_adjust = True
            ex.amount_tax = 10.0
        ex.save()
        self.assertTrue(expense.tax_adjust)
        self.assertEqual(expense.amount_tax, 10.0)
        # Create expense sheet
        sheet = self.sheet.create(
            {
                "employee_id": self.employee_admin.id,
                "name": "Expense test",
                "expense_line_ids": [(6, 0, expense.id)],
            }
        )
        sheet._compute_amount()
        self.assertEqual(sheet.state, "draft")
        self.assertEqual(sheet.total_amount, 100.0)
        self.assertEqual(sheet.total_amount_taxes, 10.0)
        self.assertEqual(sheet.untaxed_amount, 90.0)
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertTrue(sheet.account_move_id)
        self.assertEqual(len(sheet.account_move_id.line_ids), 3)
        self.assertEqual(sheet.account_move_id.amount_residual, 100.0)
        # Before adjust tax, source move line must accounting debit = 90.91
        # After adjust tax, it change accounting debit = 90 and tax debit = 10
        self.assertEqual(
            sheet.account_move_id.line_ids.filtered(
                lambda line: line.display_type == "product"
            ).debit,
            90.0,
        )
        self.assertEqual(
            sheet.account_move_id.line_ids.filtered(
                lambda line: line.display_type == "tax"
            ).debit,
            10.0,
        )

    def test_02_expense_adjust_tax_multi_currency(self):
        expense = self.expense.create(
            {
                "name": "Expense test",
                "employee_id": self.employee_admin.id,
                "product_id": self.expense_product.id,
                "currency_id": self.eur_currency.id,
                "total_amount": 100.0,
                "tax_ids": [(6, 0, [self.tax_purchase_include.id])],
            }
        )
        self.assertEqual(expense.total_amount, 100)
        self.assertFalse(expense.tax_adjust)
        self.assertEqual(expense.amount_tax, 9.09)  # (100 * 10) / 110
        self.assertAlmostEqual(expense.amount_tax_company, 13.9)  # (152.89 * 10) / 110
        # Test increase taxes adjust
        with Form(expense) as ex:
            ex.tax_adjust = True
            ex.amount_tax = 10.0
        ex.save()
        self.assertTrue(expense.tax_adjust)
        self.assertEqual(expense.amount_tax, 10.0)
        self.assertAlmostEqual(expense.amount_tax_company, 15.29)
        # Create expense sheet
        sheet = self.sheet.create(
            {
                "employee_id": self.employee_admin.id,
                "name": "Expense test",
                "expense_line_ids": [(6, 0, expense.id)],
            }
        )
        sheet._compute_amount()
        self.assertEqual(sheet.state, "draft")
        self.assertAlmostEqual(sheet.total_amount, 152.89)  # 1 EUR = 1.5289 USD
        self.assertAlmostEqual(sheet.total_amount_taxes, 15.29)
        self.assertAlmostEqual(sheet.untaxed_amount, 137.6)
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertTrue(sheet.account_move_id)
        self.assertEqual(len(sheet.account_move_id.line_ids), 3)
        self.assertAlmostEqual(sheet.account_move_id.amount_residual, 152.89)
        # Before adjust tax, source move line must accounting debit = 138.99
        # After adjust tax, it change accounting debit = 137.6 and tax debit = 15.29
        self.assertAlmostEqual(
            sheet.account_move_id.line_ids.filtered(
                lambda line: line.display_type == "product"
            ).debit,
            137.6,
        )
        self.assertAlmostEqual(
            sheet.account_move_id.line_ids.filtered(
                lambda line: line.display_type == "tax"
            ).debit,
            15.29,
        )
