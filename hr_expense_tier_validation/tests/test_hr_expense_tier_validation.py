# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpenseTierValidation(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tier_def_obj = cls.env["tier.definition"]
        # Create tier validation
        cls.tier_def_obj.create(
            {
                "model_id": cls.env.ref("hr_expense.model_hr_expense").id,
                "review_type": "individual",
                "reviewer_id": cls.expense_user_manager.id,
            }
        )

    def _create_expense(
        self,
        description,
        employee,
        product,
    ):
        with Form(self.env["hr.expense"]) as expense:
            expense.name = description
            expense.employee_id = employee
            expense.product_id = product
        expense = expense.save()
        expense.tax_ids = False  # Test no vat
        return expense

    def test_get_tier_validation_model_names(self):
        self.assertIn(
            "hr.expense", self.tier_def_obj._get_tier_validation_model_names()
        )

    def test_edit_value_expense(self):
        expense = self._create_expense(
            "Test - Expense",
            self.expense_employee,
            self.product_a,
        )
        self.assertEqual(expense.state, "draft")
        expense.action_submit()
        self.assertEqual(expense.state, "submitted")

        # Must request validation before approve
        with self.assertRaises(ValidationError):
            expense.action_approve()

        expense.request_validation()
        self.assertTrue(expense)
        expense.invalidate_model()

        # tier validation but state still submitted
        self.assertEqual(expense.state, "submitted")

        # not allow edit expense when under validation
        # Use ORM write directly: in 19.0 `name` is view-readonly on submitted
        # expenses, so a Form()-based test fails at the view layer before
        # reaching the model-level guard.
        with self.assertRaises(ValidationError):
            expense.write({"name": "Change name"})

        # test change field exception in tier, it should allow edit
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_expense.tier_exceptions", "['name']"
        )
        expense.write({"name": "Change name"})
