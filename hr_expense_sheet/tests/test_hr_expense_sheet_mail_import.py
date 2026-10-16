# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.hr_expense_sheet.tests.common import TestHrExpenseSheetCommon


@tagged("-at_install", "post_install")
class TestHrExpenseSheetMailImport(TestHrExpenseSheetCommon):
    def test_import_expense_from_mail_create_sheets_from_expense_errors(self):
        # Make sure we get the expected UserError when trying to validate an expense
        # with no product
        message = {
            "message_id": "the-world-is-a-ghetto",
            "subject": "no product code 800",
            "email_from": self.expense_user_employee.email,
            "to": "catchall@yourcompany.com",
            "body": "Don't you know, that for me, and for you",
            "attachments": [],
        }
        expense = self.env["hr.expense"].message_new(message)
        with self.assertRaisesRegex(
            UserError, "You can not create report without category."
        ):
            expense._create_sheets_from_expense()
