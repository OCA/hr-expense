# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.tests import common


class TestHrExpenseJournal(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.journal_model = cls.env["account.journal"]
        cls.payment_method_model = cls.env["account.payment.method"]
        cls.payment_method_line_model = cls.env["account.payment.method.line"]

        cls.employee_admin = cls.env.ref("hr.employee_admin")
        cls.company_admin = cls.employee_admin.company_id
        cls.product = cls.env.ref("hr_expense.product_product_no_cost")
        cls.new_journal = cls.journal_model.create(
            {
                "name": "New Journal",
                "type": "bank",
                "code": "BANK1",
            }
        )
        cls.new_method = cls.payment_method_model.sudo().create(
            {
                "name": "checks",
                "code": "check_printing_expense_test",
                "payment_type": "outbound",
            }
        )
        cls.new_payment_method_line = cls.payment_method_line_model.create(
            {
                "name": "Check",
                "payment_method_id": cls.new_method.id,
                "journal_id": cls.new_journal.id,
            }
        )

    def test_expense_payment_method_line(self):
        expense = self.expense_model.create(
            [
                {
                    "name": "Expense Line",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product.id,
                    "total_amount": 10,
                    "payment_mode": "company_account",
                    "payment_method_line_id": self.new_payment_method_line.id,
                },
            ]
        )
        expense.action_submit_expenses()
        self.assertEqual(
            expense.sheet_id.payment_method_line_id.id,
            expense.payment_method_line_id.id,
        )

    def test_payment_method_line_selectable_company(self):
        self.company_admin.company_expense_allowed_payment_method_line_ids = (
            self.new_payment_method_line
        )
        expense = self.expense_model.create(
            [
                {
                    "name": "Expense Line",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product.id,
                    "total_amount": 10,
                    "payment_mode": "company_account",
                    "payment_method_line_id": self.new_payment_method_line.id,
                },
            ]
        )
        expense._compute_selectable_payment_method_line_ids()
        selectable = expense.selectable_payment_method_line_ids
        self.assertEqual(
            selectable,
            self.new_payment_method_line,
        )
