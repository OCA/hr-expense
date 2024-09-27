# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form, new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestHrExpenseEmployeeAnalyticDefault(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = new_test_user(cls.env, login="test_user_1")
        cls.user1.action_create_employee()
        cls.work_address = cls.env["res.partner"].create({"name": "Work address"})
        cls.user1.employee_ids.address_id = cls.work_address
        cls.user2 = new_test_user(cls.env, login="test_user_2")
        cls.user2.action_create_employee()
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
            self.env["hr.expense"].with_context(
                default_employee_id=self.user1.employee_ids.id
            )
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
        expense_form.employee_id = self.user2.employee_ids
        expense = expense_form.save()
        self.assertFalse(expense.analytic_distribution)

    def test_hr_employee_2(self):
        """Create expense for employee 2 + change to employee 1."""
        expense_form = Form(
            self.env["hr.expense"].with_context(
                default_employee_id=self.user2.employee_ids.id
            )
        )
        expense_form.product_id = self.product
        expense_form.name = "Test"
        expense = expense_form.save()
        self.assertFalse(expense.analytic_distribution)
        expense_form.employee_id = self.user1.employee_ids
        expense = expense_form.save()
        self.assertEqual(
            expense.analytic_distribution, self.distribution.analytic_distribution
        )
