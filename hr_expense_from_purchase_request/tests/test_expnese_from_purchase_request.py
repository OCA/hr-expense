# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests.common import Form, TransactionCase


class TestPurchaseRequest(TransactionCase):
    def setUp(self):
        super(TestPurchaseRequest, self).setUp()
        self.purchase_request_obj = self.env["purchase.request"]
        self.purchase_request_line_obj = self.env["purchase.request.line"]
        self.user_demo = self.env.ref("base.user_demo")
        vals = {
            "picking_type_id": self.env.ref("stock.picking_type_in").id,
            "requested_by": self.user_demo.id,
        }
        self.purchase_request = self.purchase_request_obj.create(vals)
        vals = [
            {
                "request_id": self.purchase_request.id,
                "name": "PR Line 1",
                "product_id": self.env.ref("product.product_product_13").id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "product_qty": 5.0,
                "estimated_cost": 500,
            },
            {
                "request_id": self.purchase_request.id,
                "name": "PR Line 2",
                "product_id": self.env.ref("product.product_product_12").id,
                "product_uom_id": self.env.ref("uom.product_uom_unit").id,
                "product_qty": 10.0,
                "estimated_cost": 1000,
            },
        ]
        self.purchase_request_line_obj.create(vals)

    def test_expense_from_purchase_request(self):
        """ Approved PR can be used to create Expense Report """
        # Create PR
        self.purchase_request.button_to_approve()
        self.assertEqual(self.purchase_request.state, "to_approve")
        # Create Expense Report from this PR
        view_id = "hr_expense.view_hr_expense_sheet_form"
        with Form(self.env["hr.expense.sheet"], view=view_id) as expense_sheet:
            expense_sheet.name = "Expense from PR"
            expense_sheet.employee_id = self.user_demo.employee_id
            expense_sheet.purchase_request_id = self.purchase_request
        expense = expense_sheet.save()
        # PR lines is now Expense lines
        self.assertEqual(len(expense.expense_line_ids), 2)
        self.assertEqual(expense.total_amount, 1500)
        # Test not allow submit, it amount exceed
        line1 = expense.expense_line_ids.filtered(lambda l: l.name == "PR Line 1")
        line1.write({"quantity": 10})  # make amount exceed PR amount
        with self.assertRaises(UserError):
            expense.action_submit_sheet()
        line1.write({"quantity": 5})
        # Test not PR must been approved
        with self.assertRaises(UserError):
            expense.approve_expense_sheets()
        self.purchase_request.button_approved()
        self.assertEqual(self.purchase_request.state, "approved")
        expense.approve_expense_sheets()
        # Approving Expense sheet will approve PR
        self.assertEqual(self.purchase_request.state, "done")
