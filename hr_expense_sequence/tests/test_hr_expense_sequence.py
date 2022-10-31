# Copyright 2014 Serv. Tecnol. Avanzados (http://www.serviciosbaeza.com)
#                       Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase


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
        cls.expense = cls.create_expense(cls, "Expense")

    def create_expense(self, name):
        """Returns an open expense"""
        expense = self.expense_model.create(
            {
                "name": name,
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "unit_amount": self.product.standard_price,
                "quantity": 1,
            }
        )
        expense.action_submit_expenses()
        return expense

    def test_create_sequence(self):
        # Test not send number
        sheet1 = self.expense_sheet_model.create(
            {"name": "Expense Report", "employee_id": self.employee.id}
        )
        self.assertNotEqual(sheet1.number, "/")
        # Test send number '/'
        sheet2 = self.expense_sheet_model.create(
            {"name": "Expense Report", "employee_id": self.employee.id, "number": "/"}
        )
        self.assertNotEqual(sheet2.number, "/")
        # Test send number 'EX1'
        sheet_manual_number = self.expense_sheet_model.create(
            {"name": "Expense Report", "employee_id": self.employee.id, "number": "EX1"}
        )
        self.assertEqual(sheet_manual_number.number, "EX1")
        # Test duplicate expense number '/'
        sheet2.number = "/"
        expense2 = sheet2.copy()
        expense_number_2 = expense2.number
        self.assertNotEqual(sheet2.number, expense_number_2)
