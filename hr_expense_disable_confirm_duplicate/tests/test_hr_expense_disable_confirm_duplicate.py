# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import Form, TransactionCase


class TestHrExpenseSequence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.expense_sheet_model = cls.env["hr.expense.sheet"]
        cls.product = cls.env.ref("product.product_product_4")

        employee_home = cls.env["res.partner"].create({"name": "Employee Home Address"})
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Employee", "address_home_id": employee_home.id}
        )
        cls.expense1 = cls.create_expense(cls, "Expense")

    def create_expense(self, name):
        with Form(self.expense_model) as ex:
            ex.name = name
            ex.employee_id = self.employee
            ex.product_id = self.product
            ex.total_amount = self.product.standard_price
        expense = ex.save()
        return expense

    def create_expense_sheet(self, name, expense_id):
        return self.expense_sheet_model.create(
            {
                "name": name,
                "employee_id": self.employee.id,
                "expense_line_ids": [(6, 0, [expense_id])],
            }
        )

    def test_01_enable_confirm_duplicate_expense(self):
        # Create First not duplicate
        self.assertFalse(self.expense1.duplicate_expense_ids)
        # Create second, duplicate
        self.expense2 = self.create_expense("Expense")
        self.assertEqual(
            self.expense2.duplicate_expense_ids, (self.expense1 + self.expense2)
        )

        # Check duplicate when approve expense sheet
        sheet1 = self.create_expense_sheet("Sheet Test", self.expense1.id)
        sheet1.action_submit_sheet()
        action = sheet1.approve_expense_sheets()
        self.assertFalse(action)

        sheet2 = self.create_expense_sheet("Sheet Test", self.expense2.id)
        sheet2.action_submit_sheet()
        # Approve duplicate, it will redirect to confirmation wizard
        action = sheet2.approve_expense_sheets()
        self.assertTrue(action)
        self.assertEqual(
            action["xml_id"], "hr_expense.hr_expense_approve_duplicate_action"
        )

    def test_02_disable_confirm_duplicate_expense(self):
        self.env.company.disable_confirm_expense_duplicate = True
        # Create First not duplicate
        self.assertFalse(self.expense1.duplicate_expense_ids)
        # Create second, it will skip duplicate
        self.expense2 = self.create_expense("Expense")
        self.assertFalse(self.expense2.duplicate_expense_ids)

        # Check duplicate when approve expense sheet
        sheet1 = self.create_expense_sheet("Sheet Test", self.expense1.id)
        sheet1.action_submit_sheet()
        action = sheet1.approve_expense_sheets()
        self.assertFalse(action)

        sheet2 = self.create_expense_sheet("Sheet Test", self.expense2.id)
        sheet2.action_submit_sheet()
        # Skip redirect to confirmation wizard
        action = sheet2.approve_expense_sheets()
        self.assertFalse(action)
