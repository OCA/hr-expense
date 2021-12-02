# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests import Form
from odoo.tests.common import TransactionCase


class TestHrExpenseCancelConfirm(TransactionCase):
    def setUp(self):
        super().setUp()
        product = self.env["product.product"].create(
            {"name": "Product test", "type": "service"}
        )
        employee_home = self.env["res.partner"].create(
            {"name": "Employee Home Address"}
        )
        employee = self.env["hr.employee"].create(
            {"name": "Employee A", "address_home_id": employee_home.id}
        )
        self.sheet = self.env["hr.expense.sheet"].create(
            {"name": "Test expense sheet", "employee_id": employee.id}
        )
        self.expense = self.env["hr.expense"].create(
            {
                "name": "Expense test",
                "employee_id": employee.id,
                "product_id": product.id,
                "unit_amount": 50.0,
            }
        )

    def test_01_cancel_move(self):
        """
        - Cancel a expense with the wizard asking for the reason
        - Then the expense should be reverse state to submit and the reason stored
        """
        self.assertEqual(len(self.sheet.expense_line_ids), 0)
        # We add an expense
        self.sheet.expense_line_ids = [(6, 0, [self.expense.id])]
        self.assertEqual(len(self.sheet.expense_line_ids), 1)
        self.assertEqual(self.sheet.state, "draft")
        self.assertAlmostEqual(self.expense.total_amount, 50.0)
        self.sheet.action_submit_sheet()
        self.assertEqual(self.sheet.state, "submit")
        self.sheet.approve_expense_sheets()
        self.assertEqual(self.sheet.state, "approve")
        self.sheet.action_sheet_move_create()
        self.assertEqual(self.sheet.state, "post")
        # Click cance, cancel confirm wizard will open. Type in cancel_reason
        res = self.sheet.action_cancel()
        ctx = res.get("context")
        self.assertEqual(ctx["cancel_method"], "action_cancel")
        self.assertEqual(ctx["default_has_cancel_reason"], "optional")
        wizard = Form(self.env["cancel.confirm"].with_context(ctx))
        wizard.cancel_reason = "Wrong information"
        wiz = wizard.save()
        # Confirm cancel on wizard
        wiz.confirm_cancel()
        self.assertEqual(self.sheet.cancel_reason, wizard.cancel_reason)
        # state will change back to submit and still show reason until posted
        self.assertEqual(self.sheet.state, "submit")
        self.sheet.approve_expense_sheets()
        self.sheet.action_sheet_move_create()
        self.assertEqual(self.sheet.cancel_reason, False)
