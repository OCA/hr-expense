# Copyright 2025 ForgeFlow S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("post_install", "-at_install")
class TestHrExpenseSequenceAccountMove(TestExpenseCommon):
    def _post(self, sheet):
        """Run a report through to its posted journal entries.

        The entries are only created on posting: `hr_expense_invoice`, when
        installed, bypasses their creation on approval for employee-paid
        reports, so asserting right after `action_approve_expense_sheets` is
        not reliable.
        """
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        return sheet.account_move_ids

    def test_own_account_bill_gets_the_report_number(self):
        """The vendor bill of a report paid by the employee is prefixed with
        the report number, down to its payable journal item."""
        sheet = self.create_expense_report({"name": "Paid by employee"})
        expected = f"{sheet.number} - Paid by employee"
        moves = self._post(sheet)
        self.assertEqual(len(moves), 1)
        self.assertEqual(moves.state, "posted")
        self.assertEqual(moves.ref, expected)
        # Both fields must stay equal: core concatenates them into the payable
        # line label when they differ
        self.assertEqual(moves.payment_reference, expected)
        # `account.move.line.ref` is what the reconciliation widget searches on
        self.assertEqual(set(moves.line_ids.mapped("ref")), {expected})
        payable_line = moves.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        self.assertEqual(payable_line.name, expected)

    def test_company_account_payments_keep_their_own_reference(self):
        """Each payment entry of a report paid by the company keeps the
        reference of its expense line, prefixed with the report number."""
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
        expected = {
            f"{sheet.number} - Expense line 1",
            f"{sheet.number} - Expense line 2",
        }
        moves = self._post(sheet)
        # One journal entry (and payment) per expense line, each still telling
        # which expense it belongs to
        self.assertEqual(len(moves), 2)
        self.assertEqual(set(moves.mapped("state")), {"posted"})
        # The memo inverse writes back on the move reference, so it must have
        # been prefixed as well
        self.assertEqual(set(moves.origin_payment_id.mapped("memo")), expected)
        self.assertEqual(set(moves.mapped("ref")), expected)
        self.assertEqual(set(moves.line_ids.mapped("ref")), expected)

    def test_manual_number_is_propagated(self):
        """A number forced at creation is propagated as well."""
        sheet = self.create_expense_report(
            {"name": "Manual number", "number": "EX-MANUAL-1"}
        )
        moves = self._post(sheet)
        self.assertEqual(moves.ref, "EX-MANUAL-1 - Manual number")

    def test_no_number_keeps_the_standard_reference(self):
        """Without a number, the standard reference is left untouched."""
        sheet = self.create_expense_report({"name": "No number"})
        # The sequence is only consumed on creation, so emptying it afterwards
        # is the only way to get a report without number
        sheet.number = "/"
        moves = self._post(sheet)
        self.assertEqual(moves.ref, sheet.name)

    def test_number_alone_when_there_is_nothing_to_prefix(self):
        """An empty standard reference leaves the number on its own, with no
        dangling separator."""
        sheet = self.create_expense_report({"name": "To be emptied"})
        sheet.name = ""
        moves = self._post(sheet)
        self.assertEqual(moves.ref, sheet.number)
