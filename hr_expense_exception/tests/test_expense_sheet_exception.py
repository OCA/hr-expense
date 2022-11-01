# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from datetime import datetime

from odoo.tests.common import TransactionCase
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class TestExpenseSheetException(TransactionCase):
    def setUp(self):
        super(TestExpenseSheetException, self).setUp()
        # Useful models
        self.ExpenseSheet = self.env["hr.expense.sheet"]
        self.ExpenseSheetLine = self.env["hr.expense"]
        self.employee_id = self.env.ref("hr.employee_admin")
        self.product_id_1 = self.env.ref("product.product_product_6")
        self.product_id_2 = self.env.ref("product.product_product_7")
        self.product_id_3 = self.env.ref("product.product_product_7")
        self.date_expense = datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.expense_exception_confirm = self.env["expense.sheet.exception.confirm"]
        self.exception_noemail = self.env.ref("hr_expense_exception.ex_excep_no_email")
        self.exception_qtycheck = self.env.ref(
            "hr_expense_exception.exl_excep_qty_check"
        )
        self.ex_vals = {
            "employee_id": self.employee_id.id,
            "name": "My Expense Sheet",
            "expense_line_ids": [
                (
                    0,
                    0,
                    {
                        "employee_id": self.employee_id.id,
                        "name": self.product_id_1.name,
                        "product_id": self.product_id_1.id,
                        "quantity": 5.0,
                        "unit_amount": 500.0,
                        "date": self.date_expense,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "employee_id": self.employee_id.id,
                        "name": self.product_id_2.name,
                        "product_id": self.product_id_2.id,
                        "quantity": 5.0,
                        "unit_amount": 250.0,
                        "date": self.date_expense,
                    },
                ),
            ],
        }

    def test_expense_sheet_exception(self):
        self.exception_noemail.active = True
        self.exception_qtycheck.active = True
        self.employee_id.work_email = False
        self.ex = self.ExpenseSheet.create(self.ex_vals.copy())
        self.env.ref("base.user_admin")
        # submit expense sheet
        self.ex.action_submit_sheet()
        self.assertEqual(self.ex.state, "draft")
        # test all draft ex
        self.ex2 = self.ExpenseSheet.create(self.ex_vals.copy())

        self.ExpenseSheet.test_all_draft_expenses()
        self.assertEqual(self.ex2.state, "draft")
        # Set ignore_exception flag  (Done after ignore is selected at wizard)
        self.ex.ignore_exception = True
        self.ex.action_submit_sheet()
        self.assertEqual(self.ex.state, "submit")

        # Add a expense_line_ids to test after EX is submitted
        # set ignore_exception = False  (Done by onchange of expense_line_ids)
        field_onchange = self.ExpenseSheet._onchange_spec()
        self.assertEqual(field_onchange.get("expense_line_ids"), "1")
        self.env.cache.invalidate()
        self.ex3New = self.ExpenseSheet.new(self.ex_vals.copy())
        self.ex3New.ignore_exception = True
        self.ex3New.state = "submit"
        self.ex3New.onchange_ignore_exception()
        self.assertFalse(self.ex3New.ignore_exception)
        self.ex.write(
            {
                "expense_line_ids": [
                    (
                        0,
                        0,
                        {
                            "employee_id": self.employee_id.id,
                            "name": self.product_id_3.name,
                            "product_id": self.product_id_3.id,
                            "quantity": 2.0,
                            "unit_amount": 50.0,
                            "date": self.date_expense,
                        },
                    )
                ]
            }
        )

        # Set ignore exception True  (Done manually by user)
        self.ex.ignore_exception = True
        self.ex.reset_expense_sheets()
        self.assertEqual(self.ex.state, "draft")
        self.assertFalse(self.ex.ignore_exception)

        # Simulation the opening of the wizard expense_exception_confirm and
        # set ignore_exception to True
        ctx = {
            "active_id": self.ex.id,
            "active_ids": [self.ex.id],
            "active_model": self.ex._name,
        }
        ex_except_confirm = self.expense_exception_confirm.with_context(**ctx).create(
            {"ignore": True}
        )
        ex_except_confirm.action_confirm()
        self.assertTrue(self.ex.ignore_exception)
