# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo.tests import common


class TestHrExpenseJournal(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.journal_model = cls.env["account.journal"]

        cls.employee_admin = cls.env.ref("hr.employee_admin")
        cls.product = cls.env.ref("hr_expense.product_product_no_cost")
        cls.new_journal = cls.journal_model.create(
            {
                "name": "New Journal",
                "type": "bank",
                "code": "BANK1",
            }
        )

    def test_expense_journal(self):
        expense = self.expense_model.create(
            [
                {
                    "name": "Expense Line",
                    "employee_id": self.employee_admin.id,
                    "product_id": self.product.id,
                    "total_amount": 10,
                    "payment_mode": "company_account",
                    "payment_type_id": self.new_journal.id,
                },
            ]
        )
        sheet_vals = expense.action_submit_expenses()
        self.assertEqual(
            sheet_vals["context"]["default_bank_journal_id"], expense.payment_type_id.id
        )
