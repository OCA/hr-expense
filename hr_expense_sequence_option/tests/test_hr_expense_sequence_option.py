# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrExpenseSequenceOption(TransactionCase):
    def setUp(self):
        super(TestHrExpenseSequenceOption, self).setUp()
        self.HrExpenseSheet = self.env["hr.expense.sheet"]
        self.HrExpense = self.env["hr.expense"]
        self.user = self.env.ref("base.user_admin")
        self.product_id_1 = self.env.ref("hr_expense.product_product_fixed_cost")
        self.ex_vals = {
            "name": "Test Expense",
            "employee_id": self.user.employee_id.id,
            "expense_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": self.product_id_1.name,
                        "employee_id": self.user.employee_id.id,
                        "product_id": self.product_id_1.id,
                        "quantity": 1.0,
                        "unit_amount": 500.0,
                    },
                ),
            ],
        }
        self.ex_seq_opt1 = self.env.ref(
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
