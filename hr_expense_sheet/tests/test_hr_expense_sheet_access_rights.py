# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from odoo.addons.hr_expense_sheet.tests.common import TestHrExpenseSheetCommon


@tagged("-at_install", "post_install")
class TestHrExpenseSheetAccessRights(TestHrExpenseSheetCommon, HttpCase):
    @mute_logger(
        "odoo.models.unlink",
        "odoo.addons.base.models.ir_model",
        "odoo.addons.base.models.ir_rule",
    )
    def test_expense_sheet_access_rights(self):
        # The expense employee is able to a create an expense sheet.
        expense_sheet_approve = (
            self.env["hr.expense.sheet"]
            .with_user(self.expense_user_employee)
            .create(
                {
                    "name": "First Expense for employee",
                    "employee_id": self.expense_employee.id,
                    "journal_id": self.company_data["default_journal_purchase"].id,
                    "accounting_date": "2017-01-01",
                    "expense_line_ids": [
                        Command.create(
                            {
                                # Expense without foreign currency but analytic account.
                                "name": "expense_1",
                                "date": "2016-01-01",
                                "product_id": self.product_a.id,
                                "price_unit": 1000.0,
                                "employee_id": self.expense_employee.id,
                            }
                        )
                    ],
                }
            )
        )
        expense_sheet_refuse = (
            self.env["hr.expense.sheet"]
            .with_user(self.expense_user_employee)
            .create(
                {
                    "name": "Extra Expense for employee",
                    "employee_id": self.expense_employee.id,
                    "journal_id": self.company_data["default_journal_purchase"].id,
                    "accounting_date": "2017-01-01",
                    "expense_line_ids": [
                        Command.create(
                            {
                                # Expense without foreign currency but analytic account.
                                "name": "expense_2",
                                "date": "2016-01-02",
                                "product_id": self.product_a.id,
                                "price_unit": 1000.0,
                                "employee_id": self.expense_employee.id,
                            }
                        )
                    ],
                }
            )
        )
        sheets = expense_sheet_approve | expense_sheet_refuse
        self.assertRecordValues(sheets, [{"state": "draft"}, {"state": "draft"}])
        # The expense employee is able to submitted the expense sheet.
        sheets.with_user(self.expense_user_employee).action_submit()
        self.assertRecordValues(
            sheets, [{"state": "submitted"}, {"state": "submitted"}]
        )
        # The expense employee is not able to approve itself the expense sheet.
        with self.assertRaises(UserError):
            expense_sheet_approve.with_user(self.expense_user_employee).action_approve()
        with self.assertRaises(UserError):
            expense_sheet_refuse.with_user(self.expense_user_employee).action_refuse()
        self.assertRecordValues(
            sheets, [{"state": "submitted"}, {"state": "submitted"}]
        )
        # An expense manager is required for this step.
        expense_sheet_approve.with_user(self.expense_user_manager).action_approve()
        res = expense_sheet_refuse.with_user(self.expense_user_manager).action_refuse()
        wizard = (
            self.env[res["res_model"]]
            .with_context(**res["context"])
            .create({"reason": "failed"})
        )
        wizard.action_refuse()
        self.assertRecordValues(sheets, [{"state": "approved"}, {"state": "refused"}])
        # An expense manager is not able to posted the journal entry.
        with self.assertRaises(AccessError):
            expense_sheet_approve.with_user(self.expense_user_manager).action_post()
        self.assertRecordValues(expense_sheet_approve, [{"state": "approved"}])
        # An expense manager having accounting access rights is able to post the
        # journal entry.
        expense_sheet_approve.with_user(self.env.user).action_post()
        self.assertRecordValues(expense_sheet_approve, [{"state": "posted"}])

    @mute_logger("odoo.addons.base.models.ir_rule")
    def test_corner_case_expense_sheet_only_accountant_can_unlink_expenses(self):
        """
        Test that only accountant can add/remove expenses from an approved sheet
        (to manually synchronize the model with the account.move)
        """
        sheet = self.create_expense_report()
        sheet.action_submit()
        sheet.action_approve()
        new_expense = self.create_expenses()
        with self.assertRaises(UserError):
            sheet.with_user(self.expense_user_employee).expense_line_ids = [
                Command.link(new_expense.id)
            ]
        with self.assertRaises(UserError):
            sheet.with_user(self.expense_user_manager).expense_line_ids = [
                Command.link(new_expense.id)
            ]
        sheet.with_user(self.simple_accountman).expense_line_ids = [
            Command.link(new_expense.id)
        ]
