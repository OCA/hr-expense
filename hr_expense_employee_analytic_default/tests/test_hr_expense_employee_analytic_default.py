# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests import Form, common, new_test_user


class TestHrExpenseEmployeeAnalyticDefault(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(
            context=dict(
                cls.env.context,
                mail_create_nolog=True,
                mail_create_nosubscribe=True,
                mail_notrack=True,
                no_reset_password=True,
                tracking_disable=True,
            )
        )
        cls.user1 = new_test_user(
            cls.env,
            login="test_user_1",
        )
        cls.user1.action_create_employee()
        cls.work_address = cls.env["res.partner"].create(
            {
                "name": "Work address",
            }
        )
        cls.user1.employee_ids.address_id = cls.work_address
        cls.user2 = new_test_user(
            cls.env,
            login="test_user_2",
        )
        cls.user2.action_create_employee()
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Test analytic account",
            }
        )
        cls.analytic_tag = cls.env["account.analytic.tag"].create(
            {"name": "Test analytic tag"}
        )
        cls.default_rule = cls.env["account.analytic.default"].create(
            {
                "analytic_id": cls.analytic_account.id,
                "analytic_tag_ids": [(4, cls.analytic_tag.id)],
                "partner_id": cls.work_address.id,
                "date_start": "2023-01-01",
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test expense product",
                "can_be_expensed": True,
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
        self.assertEqual(expense.analytic_account_id, self.analytic_account)
        self.assertIn(self.analytic_tag, expense.analytic_tag_ids)
        expense_form.employee_id = self.user2.employee_ids
        expense = expense_form.save()
        self.assertFalse(expense.analytic_account_id)
        self.assertNotIn(self.analytic_tag, expense.analytic_tag_ids)

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
        self.assertFalse(expense.analytic_account_id)
        self.assertNotIn(self.analytic_tag, expense.analytic_tag_ids)
        expense_form.employee_id = self.user1.employee_ids
        expense = expense_form.save()
        self.assertEqual(expense.analytic_account_id, self.analytic_account)
        self.assertIn(self.analytic_tag, expense.analytic_tag_ids)
