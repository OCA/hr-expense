# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import ValidationError
from odoo.tests.common import Form, TransactionCase


class TestHrExpenseTierValidation(TransactionCase):
    def setUp(self):
        super().setUp()
        self.tier_def_obj = self.env["tier.definition"]
        self.expense_sheet_model = self.env["hr.expense.sheet"]
        self.partner = self.env.ref("base.res_partner_2")
        # Create users:
        group_ids = self.env.ref("base.group_system").ids
        self.test_user_1 = self.env["res.users"].create(
            {"name": "John", "login": "test1", "groups_id": [(6, 0, group_ids)]}
        )
        # Create tier validation
        self.tier_def_obj.create(
            {
                "model_id": self.env["ir.model"]
                .search([("model", "=", "hr.expense.sheet")])
                .id,
                "review_type": "individual",
                "reviewer_id": self.test_user_1.id,
            }
        )
        employee_home = self.env["res.partner"].create(
            {"name": "Employee Home Address"}
        )
        self.employee = self.env["hr.employee"].create(
            {"name": "Employee A", "address_home_id": employee_home.id}
        )
        self.product_1 = self.env.ref("product.product_product_1")

    def _create_expense(
        self,
        description,
        employee,
        product,
        amount,
        payment_mode="own_account",
    ):
        with Form(self.env["hr.expense"]) as expense:
            expense.name = description
            expense.employee_id = employee
            expense.product_id = product
            expense.unit_amount = amount
            expense.payment_mode = payment_mode
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
            self.employee,
            self.product_1,
            1.0,
        )
        sheet_dict = expense.action_submit_expenses()
        sheet = self.expense_sheet_model.search([("id", "=", sheet_dict["res_id"])])
        # Must request validation before submit to manager
        with self.assertRaises(ValidationError):
            sheet.action_submit_sheet()
        sheet.request_validation()
        # tier validation but state still draft
        self.assertEqual(sheet.state, "draft")
        # not allow edit expense when under validation
        with self.assertRaises(ValidationError):
            with Form(expense) as ex:
                ex.name = "New name"
        # Test change message follower
        expense.write({"message_follower_ids": self.partner.ids})
