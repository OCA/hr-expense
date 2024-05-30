# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrExpenseSequenceOption(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.HrExpenseSheet = cls.env["hr.expense.sheet"]
        cls.HrExpense = cls.env["hr.expense"]
        cls.user = cls.env.ref("base.user_admin")
        cls.product_travel = cls.env.ref(
            "hr_expense.expense_product_travel_accommodation"
        )
        cls.ex_vals = {
            "name": "Test Expense",
            "employee_id": cls.user.employee_id.id,
            "expense_line_ids": [
                Command.create(
                    {
                        "name": cls.product_travel.name,
                        "employee_id": cls.user.employee_id.id,
                        "product_id": cls.product_travel.id,
                        "quantity": 1.0,
                        "unit_amount": 500.0,
                    }
                )
            ],
        }
        cls.ex_seq_opt1 = cls.env.ref(
            "hr_expense_sequence_option.hr_expense_sequence_option"
        )

    def test_hr_expense_sequence_options(self):
        """test with and without sequence option activated"""
        # With sequence option
        self.ex_seq_opt1.use_sequence_option = True
        self.ex = self.HrExpenseSheet.create(self.ex_vals.copy())
        self.assertIn("EX-1", self.ex.number)
        # Without sequence option
        self.ex_seq_opt1.use_sequence_option = False
        self.ex = self.HrExpenseSheet.create(self.ex_vals.copy())
        self.assertNotIn("EX-1", self.ex.number)
