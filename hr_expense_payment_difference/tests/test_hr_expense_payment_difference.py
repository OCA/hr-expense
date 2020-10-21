# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import Form, SavepointCase


class TestHrExpensePaymentDifference(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.expense_sheet_model = cls.env["hr.expense.sheet"]

        cls.product = cls.env.ref("product.product_product_4")
        cls.journal_bank = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        cls.account_id = cls.env["account.account"].search([], limit=1)

        employee_home = cls.env["res.partner"].create({"name": "Employee Home Address"})
        cls.employee_1 = cls.env["hr.employee"].create(
            {"name": "Employee 1", "address_home_id": employee_home.id}
        )
        cls.expense_1 = cls.create_expense(cls, "Expense Test1")
        cls.sheet = cls.expense_sheet_model.create(
            {"name": "Report Expense 1", "employee_id": cls.employee_1.id}
        )

    def create_expense(self, name):
        """ Returns an open expense """
        expense = self.expense_model.create(
            {
                "name": name,
                "employee_id": self.employee_1.id,
                "product_id": self.product.id,
                "unit_amount": self.product.standard_price,
                "quantity": 1,
            }
        )
        expense.action_submit_expenses()
        return expense

    def test_1_create_payment_expense(self):
        self.sheet.expense_line_ids = [(6, 0, [self.expense_1.id])]
        self.sheet.action_submit_sheet()
        self.sheet.approve_expense_sheets()
        self.sheet.action_sheet_move_create()
        self.assertEqual(self.sheet.total_amount, self.product.standard_price)

        # Register Payment
        ctx = {
            "active_model": "hr.expense.sheet",
            "active_ids": [self.sheet.id],
            "active_id": self.sheet.id,
            "default_amount": self.product.standard_price,
        }
        PaymentWizard = self.env["hr.expense.sheet.register.payment.wizard"]
        with Form(PaymentWizard.with_context(ctx)) as f:
            f.journal_id = self.journal_bank
            f.amount = self.product.standard_price - 20.0
            f.payment_difference_handling = "reconcile"
            f.writeoff_account_id = self.account_id
        payment_wizard = f.save()
        self.assertEqual(payment_wizard.payment_difference, 20.0)
        payment_wizard.expense_post_payment()
        self.assertEqual(self.sheet.state, "done")
