# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.hr_expense_sheet.tests.common import TestHrExpenseSheetCommon


@tagged("-at_install", "post_install")
class TestHrExpenseSheetUi(TestHrExpenseSheetCommon, HttpCase):
    def test_not_create_zero_amount_expense_in_expense_sheet(self):
        """
        The test ensures that attempting to create an expense line with a zero amount
        fails as expected and that a valid amount can be set subsequently.
        """
        expense_sheet = self.create_expense_report(
            values={"name": "report_for_tour", "expense_line_ids": []}
        )
        with mute_logger("odoo.http"):
            self.start_tour(
                "/odoo",
                "do_not_create_zero_amount_expense_in_sheet",
                login=self.env.user.login,
            )
        self.assertEqual(
            len(expense_sheet.expense_line_ids),
            1,
            "Expense sheet should have one expense",
        )
        self.assertEqual(
            expense_sheet.expense_line_ids[0].total_amount,
            10.0,
            "Expense amount should have been set by tour",
        )

    def test_expense_sheet_access_rights_user(self):
        # The expense base user (without other rights) is able to create and read sheet
        user = new_test_user(self.env, login="test-expense", groups="base.group_user")
        expense_employee = (
            self.env["hr.employee"]
            .sudo()
            .create(
                {
                    "name": "expense_employee_base_user",
                    "user_id": user.id,
                    "work_contact_id": user.partner_id.id,
                    "address_id": user.partner_id.id,
                }
            )
        )
        expense_sheet = (
            self.env["hr.expense.sheet"]
            .with_user(user)
            .create(
                {
                    "name": "First Expense for employee",
                    "employee_id": expense_employee.id,
                    "journal_id": self.company_data["default_journal_purchase"].id,
                    "accounting_date": "2017-01-01",
                    "expense_line_ids": [
                        Command.create(
                            {
                                # Expense without foreign currency but analytic account.
                                "name": "expense_1",
                                "date": "2016-01-01",
                                "product_id": self.product_a.id,
                                "quantity": 1000.0,
                                "employee_id": expense_employee.id,
                            }
                        ),
                    ],
                }
            )
        )
        self.start_tour(
            "/odoo", "hr_expense_sheet_access_rights_test_tour", login="test-expense"
        )
        self.assertRecordValues(expense_sheet, [{"state": "submitted"}])
