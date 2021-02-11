# Copyright 2021 Open Source Integrators
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import exceptions
from odoo.tests import common


class TestHrExpense(common.SavepointCase):
    def setUp(self):
        super().setUp()
        self.Distribution = self.env["hr.expense.analytic.distribution"]
        self.Analytic = self.env["account.analytic.account"]
        self.analytic_1 = self.Analytic.create({"name": "Analytic 1"})
        self.analytic_2 = self.Analytic.create({"name": "Analytic 2"})
        self.tax_15 = self.env["account.tax"].create(
            {"name": "Tax 15%", "amount": 15.0}
        )
        self.employee_1 = self.env.ref("hr.employee_admin")
        self.product_1 = self.env.ref("hr_expense.product_product_fixed_cost")
        self.expense_1 = self.env["hr.expense"].create(
            {
                "name": "Expense Test",
                "employee_id": self.employee_1.id,
                "product_id": self.product_1.id,
                "unit_amount": 100.01,
                "payment_mode": "company_account",
                "tax_ids": [(6, 0, self.tax_15.ids)],
            }
        )
        self.expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": self.expense_1.name,
                "employee_id": self.expense_1.employee_id.id,
                "expense_line_ids": [(6, 0, self.expense_1.ids)],
            }
        )

    def test_010_distributon_not_100(self):
        with self.assertRaises(exceptions.UserError):
            self.expense_sheet.write(
                {
                    "expense_distribution_ids": [
                        (
                            0,
                            0,
                            {
                                "expense_id": self.expense_sheet.id,
                                "analytic_account_id": self.analytic_1.id,
                                "percentage": 30,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "expense_id": self.expense_sheet.id,
                                "analytic_account_id": self.analytic_2.id,
                                "percentage": 71,
                            },
                        ),
                    ]
                }
            )

    def test_020_split_expense(self):
        self.Distribution.create(
            {
                "expense_id": self.expense_sheet.id,
                "analytic_account_id": self.analytic_1.id,
                "percentage": 30,
            }
        )
        self.Distribution.create(
            {
                "expense_id": self.expense_sheet.id,
                "analytic_account_id": self.analytic_2.id,
                "percentage": 70,
            }
        )
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        account_moves = self.expense_sheet.account_move_id.line_ids
        total_debit = sum(x.debit for x in account_moves)
        total_aa2 = sum(
            x.debit for x in account_moves if x.analytic_account_id == self.analytic_2
        )
        self.assertEqual(
            total_debit,
            self.expense_sheet.total_amount,
            "Journal Entry total matches Expense Report total",
        )
        # Expense = 101.01 +15% tax = 115.01
        # 30% distribution = 34.50; 70% distribution remaining = 80.51
        self.assertEqual(total_aa2, 80.51, "Larger line takes rounding differences")
