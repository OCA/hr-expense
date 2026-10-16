# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from datetime import date

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tools import mute_logger
from odoo.tools.misc import format_date

from odoo.addons.hr_expense_sheet.tests.common import TestHrExpenseSheetCommon


class TestHrExpenseSheetMisc(TestHrExpenseSheetCommon):
    def test_expense_corner_case_changing_employee(self):
        """
        Test changing an employee on the expense that is linked with the sheet.
            - In case sheet has only one expense linked with it, than changing an
              employee on expense should trigger changing an employee
              on the sheet itself.
            - In case sheet has more than one expense linked with it, than changing
              an employee on one of the expenses,
              should cause unlinking the expense from the sheet.
        """
        employee = self.env["hr.employee"].sudo().create({"name": "Gabriel Iglesias"})
        # default employee is self.expense_employee
        expense_sheet_employee_1 = self.create_expense_report()
        expense_employee_2 = self.create_expenses({"employee_id": employee.id})
        expense_sheet_employee_1.expense_line_ids.employee_id = employee
        self.assertEqual(
            expense_sheet_employee_1.employee_id,
            employee,
            "Employee should have changed on the sheet",
        )
        expense_sheet_employee_1.expense_line_ids |= expense_employee_2
        expense_employee_2.employee_id = self.expense_employee.id
        self.assertEqual(
            expense_employee_2.sheet_id.id,
            False,
            "Sheet should be unlinked from the expense",
        )

    def test_computation_expense_report_date_based_most_recent_expense_today(self):
        """
        Test the accounting date if the most recent expense is today
        The accounting date should then be today
        """
        expense_sheet = self.create_expense_report(
            {
                "name": "Expense for John Smith",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2022-01-25",
                        }
                    ),
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 200.00,
                            "date": "2022-01-20",
                        }
                    ),
                ],
            }
        )
        expense_sheet.action_submit()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve()
            expense_sheet.action_post()
        self.assertEqual(
            expense_sheet.accounting_date, fields.Date.from_string("2022-01-25")
        )

    def test_computation_expense_report_date_based_user_input(self):
        """
        Test the accounting date if the accounting date is from the form
        The accounting date should then not be changed
        """
        expense_sheet = self.create_expense_report(
            {
                "name": "Expense for John Smith",
                "accounting_date": "2024-03-10",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2022-01-25",
                        }
                    )
                ],
            }
        )
        expense_sheet.action_submit()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve()
            expense_sheet.action_post()
        self.assertEqual(
            expense_sheet.accounting_date, fields.Date.from_string("2024-03-10")
        )

    def test_computation_expense_report_date_with_most_recent_expense_within_month_early(  # noqa: E501
        self,
    ):
        """
        Test the accounting date if the most recent expense is within this month
        but earlier than today
        The accounting date should then be today
        """
        expense_sheet = self.create_expense_report(
            {
                "name": "Expense for John Smith",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2022-01-01",
                        }
                    )
                ],
            }
        )
        expense_sheet.action_submit()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve()
            expense_sheet.action_post()
        self.assertEqual(
            expense_sheet.accounting_date, fields.Date.from_string("2022-01-25")
        )

    def test_computation_expense_report_date_with_most_recent_expense_within_month_later(  # noqa: E501
        self,
    ):
        """
        Test the accounting date if the most recent expense is within this month but
        after today
        The accounting date should then be today
        """
        expense_sheet_2 = self.create_expense_report(
            {
                "name": "Expense for John Smith",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2022-01-29",
                        }
                    )
                ],
            }
        )
        expense_sheet_2.action_submit()
        with freeze_time(self.frozen_today):
            expense_sheet_2.action_approve()
            expense_sheet_2.action_post()
        self.assertEqual(
            expense_sheet_2.accounting_date, fields.Date.from_string("2022-01-25")
        )

    def test_computation_expense_report_date_with_most_recent_expense_last_month(self):
        """
        Test the accounting date if the most recent expense is before this month
        and there is no lock date
        The accounting date should then be the last day of the mst recent expense month
        """
        expense_sheet = self.create_expense_report(
            {
                "name": "Expense for John Smith",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2021-12-20",
                        }
                    )
                ],
            }
        )
        expense_sheet.action_submit()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve()
            expense_sheet.action_post()
        # no lock date so defaults to last day of month of the most recent expense
        self.assertEqual(
            expense_sheet.accounting_date, fields.Date.from_string("2021-12-31")
        )
        expense_sheet_2 = self.create_expense_report(
            {
                "name": "Expense for John Smith 2",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2022-01-25",
                        }
                    )
                ],
            }
        )
        expense_sheet_2.action_submit()
        with freeze_time("2022-02-25"):
            expense_sheet_2.action_approve()
            expense_sheet_2.action_post()
        self.assertEqual(
            expense_sheet_2.accounting_date, fields.Date.from_string("2022-01-31")
        )

    def test_computation_expense_report_date_with_most_recent_expense_last_month_with_lock_date(  # noqa: E501
        self,
    ):
        """
        Test the accounting date if the most recent expense is before this month and
        there is a lock date
        The accounting date should then be the min(max(of the last day of most recent
        expense month AND last day of month after lock date) AND today)
        """
        self.env.company.fiscalyear_lock_date = "2021-12-31"
        expense_sheet = self.create_expense_report(
            {
                "name": "Expense for John Smith",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2021-12-20",
                        }
                    )
                ],
            }
        )
        expense_sheet.action_submit()
        with freeze_time(self.frozen_today):
            expense_sheet.action_approve()
            expense_sheet.action_post()
        # today
        self.assertEqual(
            expense_sheet.accounting_date, fields.Date.from_string("2022-01-25")
        )
        expense_sheet_2 = self.create_expense_report(
            {
                "name": "Expense for John Smith 2",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2022-01-25",
                        }
                    )
                ],
            }
        )
        expense_sheet_2.action_submit()
        with freeze_time("2022-02-25"):
            expense_sheet_2.action_approve()
            expense_sheet_2.action_post()
        self.assertEqual(
            expense_sheet_2.accounting_date, fields.Date.from_string("2022-01-31")
        )
        # another lock date
        self.env.company.fiscalyear_lock_date = "2022-01-1"
        expense_sheet_3 = self.create_expense_report(
            {
                "name": "Expense for John Smith 3",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1400.00,
                            "date": "2021-12-19",
                        }
                    )
                ],
            }
        )
        expense_sheet_3.action_submit()
        with freeze_time(self.frozen_today):
            expense_sheet_3.action_approve()
            expense_sheet_3.action_post()
        # today
        self.assertEqual(
            expense_sheet_3.accounting_date, fields.Date.from_string("2022-01-25")
        )
        expense_sheet_4 = self.create_expense_report(
            {
                "name": "Expense for John Smith 4",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1200.00,
                            "date": "2022-01-19",
                        }
                    )
                ],
            }
        )
        expense_sheet_4.action_submit()
        with freeze_time("2022-02-25"):
            expense_sheet_4.action_approve()
            expense_sheet_4.action_post()
        self.assertEqual(
            expense_sheet_4.accounting_date, fields.Date.from_string("2022-02-25")
        )

    @mute_logger("odoo.models.unlink")
    def test_accounting_date_reset_after_draft_reset(self):
        """
        Test that the accounting date is reset to False when we reset the sheet to draft
        """
        expense_sheet = self.create_expense_report(
            {
                "name": "Expense for John Smith",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "price_unit": 1000.00,
                            "date": "2021-12-20",
                        }
                    )
                ],
            }
        )
        expense_sheet.action_submit()
        self.assertEqual(
            expense_sheet.state, "submitted", "The expense sheet must be submitted"
        )
        expense_sheet.action_approve()
        self.assertEqual(
            expense_sheet.state, "approved", "The expense sheet must be approved"
        )
        expense_sheet.action_post()
        expense_sheet.expense_line_ids.account_move_id.button_draft()
        expense_sheet.expense_line_ids.account_move_id.unlink()
        expense_sheet.action_reset()
        self.assertEqual(
            expense_sheet.state, "draft", "The expense sheet must be reset to draft"
        )
        self.assertFalse(
            expense_sheet.accounting_date,
            "Accounting date must be reset when expense report is reset to draft",
        )

    def test_payment_edit_fields(self):
        """Test payment fields cannot be modified once linked with an expense"""
        sheet = self.env["hr.expense.sheet"].create(
            {
                "company_id": self.env.company.id,
                "employee_id": self.expense_employee.id,
                "name": "test sheet 2",
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "expense_1",
                            "date": "2016-01-01",
                            "product_id": self.product_c.id,
                            "total_amount": 10.0,
                            "payment_mode": "company_account",
                            "employee_id": self.expense_employee.id,
                        }
                    ),
                ],
            }
        )
        sheet.action_submit()
        sheet.action_approve()
        sheet.action_post()
        payment = sheet.account_move_ids.origin_payment_id
        with self.assertRaises(
            UserError, msg="Cannot edit payment amount after linking to an expense"
        ):
            payment.write({"amount": 500})
        payment.write({"is_sent": True})

    @mute_logger("odoo.models.unlink")
    def test_corner_case_expense_reported_cannot_be_zero(self):
        """
        Test that the expenses are not submitted if the total amount is 0.0 nor able
        to be edited that way unless unlinking it from the expense sheet.
        """
        expense = self.create_expenses(
            {"total_amount": 0.0, "total_amount_currency": 0.0}
        )
        # CASE 1: FORBIDS Trying to submit an expense with a total_amount(_currency)
        # of 0.0
        with self.assertRaises(UserError):
            expense.action_submit_expenses()
        # CASE 2: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the
        # expense is linked to a sheet + submit
        expense.total_amount_currency = 1000
        expense_sheet = expense._create_sheets_from_expense()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
            expense_sheet.action_submit()
        with self.assertRaises(UserError):
            expense.total_amount = 0.0
            expense_sheet.action_submit()
        # CASE 3: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the
        # expense sheet is approved
        expense_sheet.action_submit()
        expense_sheet.action_approve()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0
        # CASE 4: FORBIDS Trying to change the total_amount(_currency) to 0.0 when the
        # expense sheet is posted and the account move created
        expense_sheet.action_post()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
        with self.assertRaises(UserError):
            expense.total_amount = 0.0
        # CASE 5: Should behave like CASE 2, the expense is still linked to a sheet
        # after a reset to draft and shouldn't be updated
        expense_sheet.expense_line_ids.account_move_id.button_draft()
        expense_sheet.expense_line_ids.account_move_id.unlink()
        expense_sheet.action_reset()
        with self.assertRaises(UserError):
            expense.total_amount_currency = 0.0
            expense_sheet.action_submit()
        with self.assertRaises(UserError):
            expense.total_amount = 0.0
            expense_sheet.action_submit()
        # CASE 6: ALLOWS Changing the total_amount(_currency) to 0.0 when the expense
        # is unlinked from its sheet
        expense.sheet_id = False
        expense.write({"total_amount_currency": 0.0, "total_amount": 0.0})
        # CASE 7: FORBIDS Setting the amounts to 0 while setting the sheet_id
        expense.write({"total_amount_currency": 1000.0, "total_amount": 1000.0})
        with self.assertRaises(UserError):
            expense.write({"total_amount_currency": 0.0, "sheet_id": expense_sheet.id})
            expense_sheet.action_submit()
        with self.assertRaises(UserError):
            expense.write({"total_amount": 0.0, "sheet_id": expense_sheet.id})
            expense_sheet.action_submit()
        # CASE 8: ALLOWS Setting the amounts to 0 while unlinking the expense sheet
        expense.write(
            {"total_amount_currency": 0.0, "total_amount": 0.0, "sheet_id": False}
        )

    @mute_logger("odoo.models.unlink")
    def test_expense_sheet_attachments_sync(self):
        """
        Test that the hr.expense.sheet attachments stay in sync with the attachments
        associated with the expense lines
        Syncing should happen when:
        - When adding/removing expense_line_ids on a hr.expense.sheet <-> changing
          sheet_id on an expense
        - When deleting an expense that is associated with an hr.expense.sheet
        - When adding/removing an attachment of an expense that is associated with
          an hr.expense.sheet
        """

        def assert_attachments_are_synced(
            sheet, attachments_on_sheet, sheet_has_attachment
        ):
            if sheet_has_attachment:
                self.assertTrue(
                    bool(attachments_on_sheet),
                    "Attachment that belongs to the hr.expense.sheet only was "
                    "removed unexpectedly",
                )
            self.assertSetEqual(
                set(sheet.expense_line_ids.attachment_ids.mapped("checksum")),
                set((sheet.attachment_ids - attachments_on_sheet).mapped("checksum")),
                "Attachments between expenses and their sheet is not in sync.",
            )

        for sheet_has_attachment in (False, True):
            expense_1, expense_2, expense_3 = self.env["hr.expense"].create(
                [
                    {
                        "name": "expense_1",
                        "employee_id": self.expense_employee.id,
                        "product_id": self.product_c.id,
                        "total_amount": 1000,
                    },
                    {
                        "name": "expense_2",
                        "employee_id": self.expense_employee.id,
                        "product_id": self.product_c.id,
                        "total_amount": 999,
                    },
                    {
                        "name": "expense_3",
                        "employee_id": self.expense_employee.id,
                        "product_id": self.product_c.id,
                        "total_amount": 998,
                    },
                ]
            )
            self.env["ir.attachment"].create(
                [
                    {
                        "name": "test_file_1.txt",
                        "datas": base64.b64encode(b"content"),
                        "res_id": expense_1.id,
                        "res_model": "hr.expense",
                    },
                    {
                        "name": "test_file_2.txt",
                        "datas": base64.b64encode(b"other content"),
                        "res_id": expense_2.id,
                        "res_model": "hr.expense",
                    },
                    {
                        "name": "test_file_3.txt",
                        "datas": base64.b64encode(b"different content"),
                        "res_id": expense_3.id,
                        "res_model": "hr.expense",
                    },
                ]
            )
            sheet = self.env["hr.expense.sheet"].create(
                {
                    "company_id": self.env.company.id,
                    "employee_id": self.expense_employee.id,
                    "name": "test sheet",
                    "expense_line_ids": [
                        Command.set([expense_1.id, expense_2.id, expense_3.id])
                    ],
                }
            )
            sheet_attachment = (
                self.env["ir.attachment"].create(
                    {
                        "name": "test_file_4.txt",
                        "datas": base64.b64encode(b"yet another different content"),
                        "res_id": sheet.id,
                        "res_model": "hr.expense.sheet",
                    }
                )
                if sheet_has_attachment
                else self.env["ir.attachment"]
            )
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_1.attachment_ids.unlink()
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            self.env["ir.attachment"].create(
                {
                    "name": "test_file_1.txt",
                    "datas": base64.b64encode(b"content"),
                    "res_id": expense_1.id,
                    "res_model": "hr.expense",
                }
            )
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_2.sheet_id = False
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_2.sheet_id = sheet
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            sheet.expense_line_ids = [Command.set([expense_1.id, expense_3.id])]
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            expense_3.unlink()
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)
            sheet.attachment_ids.filtered(
                lambda att, sheet=sheet: att.checksum
                in sheet.expense_line_ids.attachment_ids.mapped("checksum")
            ).unlink()
            assert_attachments_are_synced(sheet, sheet_attachment, sheet_has_attachment)

    @mute_logger("odoo.models.unlink")
    def test_create_report_name(self):
        """
        When an expense sheet is created from one or more expense, the report name
        is generated through the expense name or date.
        As the expense sheet is created directly from the hr.expense.
        _create_sheets_from_expense method, we only need to test the method.
        """
        expense_with_date_1, expense_with_date_2, expense_without_date = self.env[
            "hr.expense"
        ].create(
            [
                {
                    "company_id": self.company_data["company"].id,
                    "name": f"test expense {i}",
                    "employee_id": self.expense_employee.id,
                    "product_id": self.product_a.id,
                    "date": "2021-01-01",
                    "quantity": i + 1,
                }
                for i in range(3)
            ]
        )
        expense_without_date.date = False
        # CASE 1: only one expense with or without date -> expense name
        expense_with_date_1._create_sheets_from_expense()
        self.assertEqual(
            expense_with_date_1.name,
            expense_with_date_1.sheet_id.name,
            "The report name should be the same as the expense name",
        )
        expense_with_date_1.sheet_id.unlink()
        expense_without_date._create_sheets_from_expense()
        self.assertEqual(
            expense_without_date.name,
            expense_without_date.sheet_id.name,
            "The report name should be the same as the expense name",
        )
        expense_without_date.sheet_id.unlink()
        # CASE 2: two expenses with the same date -> expense date
        expenses = expense_with_date_1 | expense_with_date_2
        expenses._create_sheets_from_expense()
        self.assertEqual(
            format_date(self.env, expense_with_date_1.date),
            expenses.sheet_id.name,
            "The report name should be the same as the expense date",
        )
        expenses.sheet_id.unlink()
        # CASE 3: two expenses with different dates -> date range
        expense_with_date_2.date = "2021-01-02"
        expenses._create_sheets_from_expense()
        date_1 = format_date(self.env, expense_with_date_1.date)
        date_2 = format_date(self.env, expense_with_date_2.date)
        self.assertEqual(
            f"{date_1} - {date_2}",
            expenses.sheet_id.name,
            "The report name should be the date range of the expenses",
        )
        expenses.sheet_id.unlink()
        # CASE 4: One or more expense doesn't have a date (single sheet) -> No
        # fallback name
        expenses |= expense_without_date
        expenses._create_sheets_from_expense()
        self.assertEqual(
            "/",
            expenses.sheet_id.name,
            "The report (with the empty expense date) name should be empty as a "
            "fallback when several reports are created",
        )
        expenses.sheet_id.unlink()
        expenses.date = False
        expenses._create_sheets_from_expense()
        self.assertEqual(
            "/", expenses.sheet_id.name, "The report name should be empty as a fallback"
        )
        expenses.sheet_id.unlink()
        # CASE 5: One or more expense doesn't have a date (multiple sheets) ->
        # Fallback name
        expenses |= self.env["hr.expense"].create(
            [
                {
                    "company_id": self.company_data["company"].id,
                    "name": f"test expense by company {i}",
                    "employee_id": self.expense_employee.id,
                    "product_id": self.product_a.id,
                    "payment_mode": "company_account",
                    "date": "2021-01-01",
                    "quantity": i + 1,
                }
                for i in range(3)
            ]
        )
        expenses._create_sheets_from_expense()
        self.assertEqual(
            [
                "New Expense Report, paid by employee",
                format_date(self.env, expenses[-1].date),
            ],
            expenses.sheet_id.mapped("name"),
        )

    def test_foreign_currencies_total(self):
        Expense = self.env["hr.expense"].with_user(self.expense_user_employee)
        Expense.create(
            [
                {
                    "name": "Company expense",
                    "payment_mode": "company_account",
                    "total_amount_currency": 1000.00,
                    "employee_id": self.expense_employee.id,
                },
                {
                    "name": "Company expense 2",
                    "payment_mode": "company_account",
                    "currency_id": self.other_currency.id,
                    "total_amount_currency": 1000.00,
                    "total_amount": 2000.00,
                    "employee_id": self.expense_employee.id,
                },
            ]
        )
        expense_state = Expense.get_expense_dashboard()
        self.assertEqual(expense_state["draft"]["amount"], 3000.00)

    @mute_logger("odoo.models.unlink", "odoo.addons.base.models.ir_rule")
    def test_expense_sheet_multi_company(self):
        self.expense_employee.sudo().company_id = self.company_data_2["company"]
        # The expense employee is able to a create an expense sheet for company_2.
        # product_a needs a standard_price in company_2
        self.product_a.with_context(
            allowed_company_ids=self.company_data_2["company"].ids
        ).standard_price = 100
        expense_sheet_approve = (
            self.env["hr.expense.sheet"]
            .with_user(self.expense_user_employee)
            .with_context(allowed_company_ids=self.company_data_2["company"].ids)
            .create(
                {
                    "name": "First Expense for employee",
                    "employee_id": self.expense_employee.id,
                    "journal_id": self.company_data_2["default_journal_purchase"].id,
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
            .with_context(allowed_company_ids=self.company_data_2["company"].ids)
            .create(
                {
                    "name": "First Expense for employee",
                    "employee_id": self.expense_employee.id,
                    "journal_id": self.company_data_2["default_journal_purchase"].id,
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
        expenses = expense_sheet_approve | expense_sheet_refuse
        self.assertRecordValues(
            expenses,
            [
                {"company_id": self.company_data_2["company"].id},
                {"company_id": self.company_data_2["company"].id},
            ],
        )
        # The expense employee is able to submit the expense sheet.
        expenses.with_user(self.expense_user_employee).action_submit()
        # An expense manager is not able to approve nor refuse without access to
        # company_2.
        with self.assertRaises(UserError):
            expense_sheet_approve.with_user(self.expense_user_manager).with_context(
                allowed_company_ids=self.company_data["company"].ids
            ).action_approve()
        with self.assertRaises(UserError):
            expense_sheet_refuse.with_user(self.expense_user_manager).with_context(
                allowed_company_ids=self.company_data["company"].ids
            )._do_refuse("failed")
        # An expense manager is able to approve/refuse with access to company_2.
        expense_sheet_approve.with_user(self.expense_user_manager).with_context(
            allowed_company_ids=self.company_data_2["company"].ids
        ).action_approve()
        expense_sheet_refuse.with_user(self.expense_user_manager).with_context(
            allowed_company_ids=self.company_data_2["company"].ids
        )._do_refuse("failed")
        # An expense manager having accounting access rights is able to post the
        # journal entry with access to company_2.
        (
            expense_sheet_approve.with_user(self.env.user)
            .with_context(allowed_company_ids=self.company_data_2["company"].ids)
            .action_post()
        )

    @mute_logger("odoo.models.unlink")
    def test_expense_sheet_with_line_ids(self):
        """
        Test to create an expense sheet with no account date and having multiple
        expenses in which one of the expense doesn't have date to get the account
        date from the max date of expenses.
        """
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Expense for John Smith",
                "employee_id": self.expense_employee.id,
                "payment_method_line_id": self.outbound_payment_method_line.id,
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "Car Travel Expenses",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 350.00,
                            "date": False,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Lunch expense",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 90.00,
                            "date": "2024-04-30",
                        }
                    ),
                ],
            }
        )
        # Validate the values before submitting and approving
        self.assertRecordValues(
            expense_sheet,
            [
                {
                    "total_amount": 440.00,
                    "accounting_date": False,
                    "state": "draft",
                    "employee_id": self.expense_employee.id,
                }
            ],
        )
        self.assertRecordValues(
            expense_sheet.expense_line_ids,
            [
                {"name": "Car Travel Expenses", "total_amount": 350.00, "date": False},
                {
                    "name": "Lunch expense",
                    "total_amount": 90.00,
                    "date": date(2024, 4, 30),
                },
            ],
        )
        expense_sheet.action_submit()
        expense_sheet.action_approve()
        expense_sheet.action_post()
        # Validate the record values after submitting and approving
        self.assertRecordValues(
            expense_sheet,
            [
                {
                    "total_amount": 440.00,
                    "accounting_date": date(2024, 4, 30),
                    "state": "posted",
                    "employee_id": self.expense_employee.id,
                }
            ],
        )
        self.assertRecordValues(
            expense_sheet.expense_line_ids,
            [
                {"name": "Car Travel Expenses", "total_amount": 350.00, "date": False},
                {
                    "name": "Lunch expense",
                    "total_amount": 90.00,
                    "date": date(2024, 4, 30),
                },
            ],
        )
        # Reset to draft to make the accounting_date to False and then recompute it
        expense_sheet.expense_line_ids.account_move_id.button_draft()
        expense_sheet.expense_line_ids.account_move_id.unlink()
        expense_sheet.action_reset()
        # Validate the accounting_date value to be false
        self.assertFalse(expense_sheet.accounting_date)
        # Update one of the expense sheet line date
        expense_sheet.expense_line_ids[1].write({"date": "2024-05-30"})
        expense_sheet.action_submit()
        expense_sheet.action_approve()
        expense_sheet.action_post()
        # Validate the acction_date value after subitting and approving
        self.assertTrue(expense_sheet.accounting_date, date(2024, 5, 30))
