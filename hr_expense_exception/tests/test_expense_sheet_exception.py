# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import json
from datetime import datetime

from odoo import Command
from odoo.tests.common import TransactionCase
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.base_exception.exceptions import BaseExceptionError


class TestExpenseSheetException(TransactionCase):
    def setUp(self):
        super().setUp()
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
                Command.create(
                    {
                        "employee_id": self.employee_id.id,
                        "name": self.product_id_1.name,
                        "product_id": self.product_id_1.id,
                        "quantity": 5.0,
                        "price_unit": 500.0,
                        "date": self.date_expense,
                    },
                ),
                Command.create(
                    {
                        "employee_id": self.employee_id.id,
                        "name": self.product_id_2.name,
                        "product_id": self.product_id_2.id,
                        "quantity": 5.0,
                        "price_unit": 250.0,
                        "date": self.date_expense,
                    },
                ),
            ],
        }

    def _assert_blocked_by_exception(self, method, target_model):
        """Call method and check that base_exception blocks it.

        In tests, base_exception writes the exceptions with the test cursor.
        Catch the error without assertRaises, which would roll them back.
        """
        try:
            method()
        except BaseExceptionError as error:
            values = json.loads(error.args[0])
            self.assertEqual(values["target_model"], target_model)
        else:
            self.fail("BaseExceptionError not raised")

    def test_expense_sheet_exception(self):
        self.exception_noemail.active = True
        self.exception_qtycheck.active = True
        self.employee_id.work_email = False
        self.ex = self.ExpenseSheet.create(self.ex_vals.copy())
        self.env.ref("base.user_admin")
        # submit expense sheet
        self._assert_blocked_by_exception(
            self.ex.action_submit_sheet, "hr.expense.sheet"
        )
        self.assertEqual(self.ex.state, "draft")
        self.assertIn(self.exception_noemail, self.ex.exception_ids)
        action = self.ex.action_popup_exceptions()
        self.assertEqual(action["res_model"], "expense.sheet.exception.confirm")
        # test all draft ex
        self.ex2 = self.ExpenseSheet.create(self.ex_vals.copy())

        self.assertTrue(self.ExpenseSheet.test_all_draft_expenses())
        self.assertEqual(self.ex2.state, "draft")
        self.assertIn(self.exception_noemail, self.ex2.exception_ids)
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
                    Command.create(
                        {
                            "employee_id": self.employee_id.id,
                            "name": self.product_id_3.name,
                            "product_id": self.product_id_3.id,
                            "quantity": 2.0,
                            "price_unit": 50.0,
                            "date": self.date_expense,
                        },
                    )
                ]
            }
        )

        # Set ignore exception True  (Done manually by user)
        self.ex.ignore_exception = True
        self.ex.action_reset_expense_sheets()
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

    def test_expense_line_exception(self):
        self.exception_qtycheck.active = True
        self.employee_id.work_email = "admin@example.com"
        sheet = self.ExpenseSheet.create(self.ex_vals.copy())
        sheet.expense_line_ids[0].quantity = -1
        self._assert_blocked_by_exception(sheet.action_submit_sheet, "hr.expense.sheet")
        self.assertEqual(sheet.state, "draft")
        self.assertIn(self.exception_qtycheck, sheet.exception_ids)
        sheet.ignore_exception = True
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
