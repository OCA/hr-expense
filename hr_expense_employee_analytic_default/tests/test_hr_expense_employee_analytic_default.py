# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged("post_install", "-at_install")
class TestHrExpenseEmployeeAnalyticDefault(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.work_address = cls.env["res.partner"].create({"name": "Work address"})

        cls.user1 = new_test_user(
            cls.env,
            name="Test User 1",
            login="test_user_1",
            groups="base.group_user",
        )
        cls.employee_1 = cls.env["hr.employee"].create(
            {
                "name": "Test Employee 1",
                "user_id": cls.user1.id,
                "address_id": cls.work_address.id,
                "work_contact_id": cls.work_address.id,
            }
        )

        cls.user2 = new_test_user(
            cls.env,
            name="Test User 2",
            login="test_user_2",
            groups="base.group_user",
        )
        cls.employee_2 = cls.env["hr.employee"].create(
            {
                "name": "Test Employee 2",
                "user_id": cls.user2.id,
            }
        )

        cls.user3 = new_test_user(
            cls.env,
            name="Test User 3",
            login="test_user_3",
            groups="base.group_user",
        )
        cls.employee_3 = cls.env["hr.employee"].create(
            {
                "name": "Test Employee 3",
                "user_id": cls.user3.id,
            }
        )
        cls.employee_3.write(
            {"address_id": False, "work_contact_id": cls.work_address.id}
        )

        cls.plan = cls.env["account.analytic.plan"].create({"name": "Test plan"})
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Test analytic account",
                "plan_id": cls.plan.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test expense product",
                "can_be_expensed": True,
            }
        )
        cls.distribution = cls.env["account.analytic.distribution.model"].create(
            {
                "product_id": cls.product.id,
                "partner_id": cls.work_address.id,
                "analytic_distribution": {str(cls.analytic_account.id): 100.0},
            }
        )

    def test_hr_employee_1(self):
        """Create expense for employee 1 + change to employee 2."""
        expense_form = Form(
            self.env["hr.expense"].with_context(default_employee_id=self.employee_1.id)
        )
        expense_form.product_id = self.product
        expense_form.name = "Test"
        expense = expense_form.save()
        self.assertEqual(
            expense.analytic_distribution, self.distribution.analytic_distribution
        )
        # As defined in _compute_analytic_distribution() of hr.expense, we need to
        # leave the value empty because if there is no analytic distribution to apply,
        # leave the value it had (maybe it is somewhat questionable).
        expense.analytic_distribution = False
        expense_form.employee_id = self.employee_2
        expense = expense_form.save()
        self.assertFalse(expense.analytic_distribution)

    def test_hr_employee_2(self):
        """Create expense for employee 2 + change to employee 1."""
        expense_form = Form(
            self.env["hr.expense"].with_context(default_employee_id=self.employee_2.id)
        )
        expense_form.product_id = self.product
        expense_form.name = "Test"
        expense = expense_form.save()
        self.assertFalse(expense.analytic_distribution)
        expense_form.employee_id = self.employee_1
        expense = expense_form.save()
        self.assertEqual(
            expense.analytic_distribution, self.distribution.analytic_distribution
        )

    def test_hr_employee_3_work_contact_fallback(self):
        """Employee with only work_contact_id (no address_id) resolves via fallback."""
        self.assertFalse(self.employee_3.address_id)
        self.assertEqual(self.employee_3.work_contact_id, self.work_address)
        expense_form = Form(
            self.env["hr.expense"].with_context(default_employee_id=self.employee_3.id)
        )
        expense_form.product_id = self.product
        expense_form.name = "Test"
        expense = expense_form.save()
        self.assertEqual(
            expense.analytic_distribution, self.distribution.analytic_distribution
        )
