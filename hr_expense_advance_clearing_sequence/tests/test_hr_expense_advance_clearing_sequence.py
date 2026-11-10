# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests import tagged

from odoo.addons.hr_expense_advance_clearing.tests.test_hr_expense_advance_clearing import (  # noqa: E501
    TestHrExpenseAdvanceClearing,
)


@tagged("-at_install", "post_install")
class TestHrExpenseAdvanceClearingSequence(TestHrExpenseAdvanceClearing):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_create_sequence_from_sheet(self):
        advance_sheet = self.advance
        self.assertNotEqual(advance_sheet.number, "/", "Number create")
        self.assertNotEqual(advance_sheet.number.find("AV"), -1)
        # Test duplicate advance, number should be different
        self.assertNotEqual(
            advance_sheet.number, advance_sheet.copy().number, "Numbers are different"
        )

    def test_02_create_several_advances(self):
        expenses = self.env["hr.expense"]
        for name in ("Advance A", "Advance B"):
            expenses |= self._create_expense(
                name, self.expense_employee, self.emp_advance, 100.0, True
            )
        sheets = self.env["hr.expense.sheet"].create(
            [
                {
                    "name": expense.name,
                    "employee_id": self.expense_employee.id,
                    "expense_line_ids": [(6, 0, expense.ids)],
                    "advance": True,
                }
                for expense in expenses
            ]
        )
        self.assertEqual(sheets.mapped("name"), ["Advance A", "Advance B"])
        self.assertIn("AV", sheets[0].number)
        self.assertIn("AV", sheets[1].number)
        self.assertNotEqual(sheets[0].number, sheets[1].number)
