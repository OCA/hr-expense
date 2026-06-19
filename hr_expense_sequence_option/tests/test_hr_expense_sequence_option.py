# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestHrExpenseSequenceOption(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.HrExpense = cls.env["hr.expense"]
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test expense product",
                "standard_price": 500.0,
                "list_price": 500.0,
                "can_be_expensed": True,
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Test Employee"})

        cls.option_sequence = cls.env["ir.sequence"].create(
            {
                "name": "Test Expense: Option 1",
                "padding": 5,
                "prefix": "EX-1/",
            }
        )
        cls.ex_seq_opt1 = cls.env["ir.sequence.option"].create(
            {
                "name": "Test Expense",
                "model": "hr.expense",
                "use_sequence_option": False,
            }
        )
        cls.env["ir.sequence.option.line"].create(
            {
                "base_id": cls.ex_seq_opt1.id,
                "name": "EX Option 1",
                "filter_domain": "[]",
                "sequence_id": cls.option_sequence.id,
            }
        )
        cls.ex_vals = {
            "name": "Test Expense",
            "employee_id": cls.employee.id,
            "product_id": cls.product.id,
            "quantity": 1,
            "total_amount_currency": 500.0,
        }

    def test_hr_expense_sequence_options_on(self):
        """When use_sequence_option=True, the option-1 sequence (EX-1) wins."""
        self.ex_seq_opt1.use_sequence_option = True
        expense = self.HrExpense.create(self.ex_vals.copy())
        self.assertIn("EX-1", expense.number)

    def test_hr_expense_sequence_options_off(self):
        """When use_sequence_option=False, the base hr_expense_sequence prefix wins."""
        self.ex_seq_opt1.use_sequence_option = False
        expense = self.HrExpense.create(self.ex_vals.copy())
        self.assertNotIn("EX-1", expense.number)
