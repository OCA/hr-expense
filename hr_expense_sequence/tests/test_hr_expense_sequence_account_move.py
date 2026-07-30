# Copyright 2025 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("post_install", "-at_install")
class TestHrExpenseSequenceAccountMove(TestExpenseCommon):
    def _approve(self, sheet):
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        return sheet.account_move_ids

    def test_own_account_bill_gets_the_report_number(self):
        """The vendor bill of a report paid by the employee is referenced by
        the report number, down to its payable journal item."""
        sheet = self.create_expense_report({"name": "Paid by employee"})
        moves = self._approve(sheet)
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves.ref, sheet.number)
        self.assertEqual(moves.payment_reference, sheet.number)
        # `account.move.line.ref` is what the reconciliation widget searches on
        self.assertEqual(set(moves.line_ids.mapped("ref")), {sheet.number})
        payable_line = moves.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        self.assertEqual(payable_line.name, sheet.number)

        sheet.action_sheet_move_post()
        self.assertEqual(moves.state, "posted")
        self.assertEqual(moves.ref, sheet.number)
        self.assertEqual(set(moves.line_ids.mapped("ref")), {sheet.number})

    def test_company_account_payments_get_the_report_number(self):
        """Every payment entry of a report paid by the company is referenced by
        the report number."""
        sheet = self.create_expense_report(
            {
                "name": "Paid by company",
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": f"Expense line {index}",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 100.00 * index,
                            "payment_mode": "company_account",
                            "date": self.frozen_today,
                            "company_id": self.company_data["company"].id,
                        }
                    )
                    for index in (1, 2)
                ],
            }
        )
        moves = self._approve(sheet)
        # One journal entry (and payment) per expense line
        self.assertEqual(len(moves), 2)
        self.assertEqual(set(moves.mapped("ref")), {sheet.number})
        self.assertEqual(set(moves.line_ids.mapped("ref")), {sheet.number})

        sheet.action_sheet_move_post()
        self.assertEqual(set(moves.mapped("state")), {"posted"})
        # The memo inverse writes back on the move reference, so it must have
        # been set to the number as well
        self.assertEqual(set(moves.origin_payment_id.mapped("memo")), {sheet.number})
        self.assertEqual(set(moves.mapped("ref")), {sheet.number})
        self.assertEqual(set(moves.line_ids.mapped("ref")), {sheet.number})

    def test_manual_number_is_propagated(self):
        """A number forced at creation is propagated as well."""
        sheet = self.create_expense_report(
            {"name": "Manual number", "number": "EX-MANUAL-1"}
        )
        moves = self._approve(sheet)
        self.assertEqual(moves.ref, "EX-MANUAL-1")

    def test_no_number_keeps_the_standard_reference(self):
        """Without a number, the standard reference is left untouched."""
        sheet = self.create_expense_report({"name": "No number"})
        # The sequence is only consumed on creation, so emptying it afterwards
        # is the only way to get a report without number
        sheet.number = "/"
        moves = self._approve(sheet)
        self.assertEqual(moves.ref, sheet.name)
