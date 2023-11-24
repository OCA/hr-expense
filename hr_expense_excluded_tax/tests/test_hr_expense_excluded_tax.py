# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


class TestHrExpenseExcludedTax(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.exp_object = cls.env["hr.expense"]
        cls.employee_admin = cls.env.ref("hr.employee_admin")
        cls.product = cls.env.ref("hr_expense.trans_expense_product")
        cls.tax_exclude = cls.env["account.tax"].create(
            {
                "name": "TAX 10%",
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "amount": 10.0,
            }
        )
        cls.tax_include = cls.env["account.tax"].create(
            {
                "name": "TAX 10% (Incl.)",
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "amount": 10.0,
                "price_include": True,
            }
        )

    def test_01_expense_excluded_tax(self):
        expense = self.exp_object.create(
            {
                "name": "Expense test",
                "employee_id": self.employee_admin.id,
                "product_id": self.product.id,
                "unit_amount": 100,
                "tax_ids": self.tax_exclude.ids,
                "payment_mode": "company_account",
                "quantity": 1,
            }
        )
        self.assertAlmostEqual(expense.untaxed_amount, 100.0)
        self.assertAlmostEqual(expense.total_amount, 110.0)

    def test_02_expense_included_tax(self):
        expense = self.exp_object.create(
            {
                "name": "Expense test",
                "employee_id": self.employee_admin.id,
                "product_id": self.product.id,
                "unit_amount": 100,
                "tax_ids": self.tax_include.ids,
                "payment_mode": "company_account",
                "quantity": 1,
            }
        )
        self.assertAlmostEqual(expense.untaxed_amount, 90.91)
        self.assertAlmostEqual(expense.total_amount, 100.0)
