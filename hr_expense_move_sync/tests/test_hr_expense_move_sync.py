# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests.common import TransactionCase


class TestHrExpenseMoveSync(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.expense_model = cls.env["hr.expense"]
        cls.product = cls.env["product.product"].create(
            {"name": "Test Expense Product", "type": "service"}
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Test Employee"})
        cls.tax = cls.env["account.tax"].create(
            {
                "name": "Test Tax 10%",
                "amount": 10.0,
                "amount_type": "percent",
            }
        )
        cls.expense_journal = cls.env["account.journal"].create(
            {
                "name": "Test Expense Journal",
                "type": "purchase",
                "code": "TEXJ",
            }
        )
        # Company-account setup
        cls.outstanding_account = cls.env["account.account"].create(
            {
                "code": "610010",
                "name": "Expense Outstanding Account",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )
        cls.payment_method_line = cls.env["account.payment.method.line"].search(
            [], limit=1
        )

    def _enable_auto_refresh(self):
        self.env.company.auto_refresh_account_moves = True

    def _ensure_draft_move(self, sheet):
        """Return a draft account.move for the approved sheet.

        Without hr_expense_invoice, approving the sheet already creates a
        draft move. With it, own_account sheets get no move at approval, so
        we post then reset to draft to reach the same state.
        """
        move = sheet.account_move_ids
        if move and move.state == "draft":
            return move
        sheet.action_sheet_move_post()
        move = sheet.account_move_ids
        move.button_draft()
        return move

    def _create_expense(
        self, name, total_amount, tax_ids=None, payment_mode="own_account"
    ):
        """Create, submit, and approve an expense. Returns the sheet."""
        expense = self.expense_model.create(
            {
                "name": name,
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "total_amount": total_amount,
                "payment_mode": payment_mode,
                "tax_ids": [Command.set(tax_ids)] if tax_ids else False,
            }
        )
        expense.action_submit_expenses()
        sheet = expense.sheet_id
        sheet.journal_id = self.expense_journal
        if payment_mode == "company_account":
            sheet.payment_method_line_id = self.payment_method_line
            self.env.company.expense_outstanding_account_id = self.outstanding_account
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        return sheet

    def test_01_manual_button_sync(self):
        """Default manual mode: edit does not sync, button click does."""
        # Default = manual (auto_refresh=False), no auto-refresh
        sheet = self._create_expense("Manual Sync", 200.0, [self.tax.id])
        move = self._ensure_draft_move(sheet)
        self.assertTrue(move)
        self.assertTrue(move.line_ids.filtered("tax_line_id"))
        self.assertEqual(move.amount_total, 200.0)

        # Edit, should NOT auto-refresh
        expense = sheet.expense_line_ids
        expense.write({"tax_ids": False, "total_amount": 500.0})

        # Move unchanged (manual mode)
        self.assertEqual(sheet.account_move_ids, move)
        self.assertTrue(move.line_ids.filtered("tax_line_id"))
        self.assertEqual(move.amount_total, 200.0)

        # Click the button
        sheet.action_sync_account_moves()

        # Now regenerated
        new_move = sheet.account_move_ids
        self.assertEqual(len(new_move), 1)
        self.assertNotEqual(new_move, move)
        self.assertEqual(new_move.amount_total, 500.0)
        self.assertFalse(new_move.line_ids.filtered("tax_line_id"))

    def test_02_auto_sync(self):
        """Auto mode: edit auto-regenerates, same result as button."""
        self._enable_auto_refresh()
        sheet = self._create_expense("Auto Sync", 200.0, [self.tax.id])
        move = self._ensure_draft_move(sheet)
        self.assertTrue(move)
        self.assertTrue(move.line_ids.filtered("tax_line_id"))
        self.assertEqual(move.amount_total, 200.0)

        # Edit, should auto-refresh
        expense = sheet.expense_line_ids
        expense.write({"tax_ids": False, "total_amount": 500.0})

        # Move regenerated automatically
        new_move = sheet.account_move_ids
        self.assertEqual(len(new_move), 1)
        self.assertNotEqual(new_move, move)
        self.assertEqual(new_move.amount_total, 500.0)
        self.assertFalse(new_move.line_ids.filtered("tax_line_id"))

    def test_03_posted_move_not_synced(self):
        """Posted moves should not be regenerated."""
        self._enable_auto_refresh()
        sheet = self._create_expense("Posted Move", 100.0, [self.tax.id])
        move = self._ensure_draft_move(sheet)
        self.assertTrue(move)

        # Post the move
        sheet.action_sheet_move_post()
        self.assertNotEqual(sheet.state, "approve")
        self.assertEqual(move.state, "posted")

        # Edit, should NOT regenerate (sheet no longer in approve state)
        expense = sheet.expense_line_ids
        expense.write({"total_amount": 999.0})

        # Move unchanged, still the same posted move
        self.assertEqual(sheet.account_move_ids, move)
        self.assertEqual(move.state, "posted")
        self.assertEqual(move.amount_total, 100.0)

    def test_04_company_account_sync(self):
        """Company-paid (company_account): sync handles payments correctly."""
        self._enable_auto_refresh()
        sheet = self._create_expense(
            "Company Paid", 300.0, payment_mode="company_account"
        )
        moves = self._ensure_draft_move(sheet)
        self.assertTrue(moves)
        self.assertEqual(moves.state, "draft")
        payment = moves.origin_payment_id
        self.assertTrue(payment)
        self.assertEqual(payment.amount, 300.0)

        # Edit, auto-refresh deletes old payment+move and recreates
        expense = sheet.expense_line_ids
        expense.write({"total_amount": 750.0})

        # Old move deleted, new one created
        new_moves = sheet.account_move_ids
        self.assertEqual(len(new_moves), 1)
        self.assertNotEqual(new_moves, moves)
        self.assertEqual(new_moves.state, "draft")

        # Old payment deleted, new payment created with new amount
        new_payment = new_moves.origin_payment_id
        self.assertTrue(new_payment)
        self.assertNotEqual(new_payment, payment)
        self.assertEqual(new_payment.amount, 750.0)

    def test_05_reset_to_draft_no_refresh(self):
        """Resetting a posted expense move to draft must not refresh the move.

        When a posted move is reset to draft, the linked sheet recomputes its
        state back to 'approve' (all moves draft). Without protection, the
        auto-refresh would unlink the very move being reset, raising
        "Record does not exist or has been deleted".
        """
        self._enable_auto_refresh()
        sheet = self._create_expense("Reset Draft", 100.0, [self.tax.id])
        move = self._ensure_draft_move(sheet)
        self.assertEqual(sheet.state, "approve")
        self.assertEqual(move.state, "draft")

        # Post the move, then reset it back to draft.
        sheet.action_sheet_move_post()
        self.assertEqual(move.state, "posted")

        move.button_draft()

        # The same move must still exist, in draft, and the sheet back to approve.
        self.assertTrue(move.exists())
        self.assertEqual(move.state, "draft")
        self.assertEqual(sheet.account_move_ids, move)
        self.assertEqual(sheet.state, "approve")
