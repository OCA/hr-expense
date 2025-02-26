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
                "model_id": cls.env.ref("hr_expense.model_hr_expense_sheet").id,
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
            "hr.expense.sheet", self.tier_def_obj._get_tier_validation_model_names()
        )

    def test_edit_value_expense(self):
        expense = self._create_expense(
            "Test - Expense",
            self.expense_employee,
            self.product_a,
        )
        sheet_dict = expense.action_submit_expenses()

        with Form(self.env["hr.expense.sheet"]) as sheet:
            sheet.name = (sheet_dict["name"],)
            sheet.employee_id = self.expense_employee
        sheet = sheet.save()
        sheet.expense_line_ids = [(6, 0, expense.id)]
        self.assertEqual(sheet.state, "draft")
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        # Must request validation before approve
        with self.assertRaises(ValidationError):
            sheet.action_approve_expense_sheets()
        sheet.request_validation()
        self.assertTrue(sheet)
        sheet.invalidate_model()
        # tier validation but state still submit
        self.assertEqual(sheet.state, "submit")
        # not allow edit expense when under validation
        with self.assertRaises(ValidationError):
            sheet.review_ids = [(6, 0, self.expense_user_manager.ids)]
        with self.assertRaises(ValidationError):
            with Form(expense) as exp:
                exp.name = "Change name"
        # test change field exception in tier, it should allow edit
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_expense.tier_exceptions", "['name']"
        )
        with Form(expense) as exp:
            exp.name = "Change name"

        message = expense._message_subscribe(self.partner_a.ids)
        self.assertTrue(message, True)
