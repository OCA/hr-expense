# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date

from odoo.tests.common import TransactionCase


class TestHrExpenseSheet(TransactionCase):
    def setUp(self):
        super().setUp()
        self.payment_term = self.env["account.payment.term"].create(
            {
                "name": "Test Payment Term",
                "line_ids": [(0, 0, {"days": 15})],
            }
        )
        self.expense_sheet = self.env.ref("hr_expense.travel_ny_sheet")

    def test_with_due_date(self):
        expense_sheet = self.expense_sheet
        expense_sheet.write(
            {
                "accounting_date": "2024-08-05",
                "due_date": "2024-09-30",
            }
        )
        expense_sheet.action_sheet_move_create()
        account_move = expense_sheet.account_move_id
        self.assertTrue(account_move)
        move_lines = account_move.line_ids
        self.assertGreater(len(move_lines), 0)

        # Filter out payable lines with date_maturity set
        payable_lines = move_lines.filtered(
            lambda l: l.account_id.internal_type == "payable" and l.date_maturity
        )

        # Correct comparison using a date object
        expected_date_maturity = date(2024, 9, 30)
        for line in payable_lines:
            self.assertEqual(
                line.date_maturity,
                expected_date_maturity,
                (
                    f"Expected date_maturity to be {expected_date_maturity} "
                    f"but got {line.date_maturity}"
                ),
            )

    def test_with_payment_term(self):
        expense_sheet = self.expense_sheet
        expense_sheet.write(
            {
                "accounting_date": "2024-08-05",
                "payment_term_id": self.payment_term.id,
            }
        )
        expense_sheet.action_sheet_move_create()
        account_move = expense_sheet.account_move_id
        self.assertTrue(account_move)
        move_lines = account_move.line_ids
        self.assertGreater(len(move_lines), 0)

        # Filter out payable lines with date_maturity set
        payable_lines = move_lines.filtered(
            lambda l: l.account_id.internal_type == "payable" and l.date_maturity
        )

        # Correct comparison using a date object
        expected_date_maturity = date(2024, 8, 20)
        for line in payable_lines:
            self.assertEqual(
                line.date_maturity,
                expected_date_maturity,
                (
                    f"Expected date_maturity to be {expected_date_maturity} "
                    f"but got {line.date_maturity}"
                ),
            )
