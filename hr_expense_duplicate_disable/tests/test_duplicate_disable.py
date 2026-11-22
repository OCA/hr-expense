# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import TransactionCase


class TestDuplicateDisable(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context={"tracking_disable": True})
        cls.Employee = cls.env["hr.employee"]
        cls.Product = cls.env["product.product"]
        cls.Expense = cls.env["hr.expense"]
        # Create employee
        cls.employee = cls.Employee.create({"name": "Test Employee"})
        # Create product
        cls.product = cls.Product.create({"name": "Test Product", "type": "service"})

    def _create_expense(self, employee, product, amount):
        return self.Expense.create(
            {
                "employee_id": employee.id,
                "product_id": product.id,
                "total_amount_currency": amount,
                "name": "Test Expense",
            }
        )

    def test_01_duplicate_detected_when_enabled(self):
        """When duplicate detection is disable, duplicates should be found."""
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_expense_disable_duplicate_detection", "False"
        )
        exp1 = self._create_expense(self.employee, self.product, 100.0)
        exp2 = self._create_expense(self.employee, self.product, 100.0)
        exp1._compute_duplicate_expense_ids()
        exp2._compute_duplicate_expense_ids()
        self.assertTrue(
            exp2.duplicate_expense_ids,
            "Duplicates should be detected when detection is enabled",
        )

    def test_02_duplicate_not_detected_when_disabled(self):
        """When duplicate detection is disabled, no duplicates should be found."""
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_expense_disable_duplicate_detection", "True"
        )
        exp1 = self._create_expense(self.employee, self.product, 100.0)
        exp2 = self._create_expense(self.employee, self.product, 100.0)
        exp1._compute_duplicate_expense_ids()
        exp2._compute_duplicate_expense_ids()
        self.assertFalse(
            exp2.duplicate_expense_ids,
            "Duplicates should NOT be detected when detection is disabled",
        )
