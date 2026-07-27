# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpenseCancel(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense = cls.create_expenses({"payment_mode": "own_account"})
        cls.expense.action_submit()
        # action_submit auto-approves when the employee has no manager;
        # only call action_approve when still in submitted state.
        if cls.expense.state == "submitted":
            cls.expense.action_approve()

    def _get_payment_wizard(self):
        action = self.expense.action_pay()
        wizard_form = Form(
            self.env[action["res_model"]].with_context(**action["context"])
        )
        wizard_form.journal_id = self.company_data["default_journal_bank"]
        wizard_form.amount = self.expense.total_amount
        return wizard_form.save()

    def test_action_reset_unposted(self):
        """Reset on a posted-but-unpaid employee expense reverses the move."""
        self.post_expenses_with_wizard(self.expense)
        self.assertTrue(self.expense.account_move_id)
        self.expense.action_reset()
        self.assertEqual(self.expense.state, "draft")

    def test_employee_reset_without_move_needs_no_accounting_access(self):
        """Employee reset of a moveless expense touches no accounting model."""
        expense = self.create_expenses(
            {"payment_mode": "own_account", "total_amount_currency": 42.0}
        )
        expense.action_submit()
        expense.with_user(self.expense_user_employee).action_reset()
        self.assertEqual(expense.state, "draft")

    def test_action_reset_paid_own_account(self):
        """Reset on a paid employee expense draft-cancels the payment +
        unreconciles before reversing the move."""
        self.post_expenses_with_wizard(self.expense)
        wizard = self._get_payment_wizard()
        wizard.action_create_payments()
        payments = self.expense.account_move_id.reconciled_payment_ids
        self.assertTrue(payments)
        self.expense.action_reset()
        self.assertEqual(set(payments.mapped("state")), {"canceled"})
        self.assertEqual(self.expense.state, "draft")

    def test_action_reset_cancels_unreconciled_wizard_payment(self):
        """Reset still cancels a wizard payment whose reconciliation was
        removed: it stays linked through core's matched_payment_ids."""
        self.post_expenses_with_wizard(self.expense)
        wizard = self._get_payment_wizard()
        wizard.action_create_payments()
        payments = self.expense.account_move_id.reconciled_payment_ids
        self.expense.account_move_id.line_ids.remove_move_reconcile()
        self.expense.action_reset()
        self.assertEqual(set(payments.mapped("state")), {"canceled"})
        self.assertEqual(self.expense.state, "draft")

    def test_action_reset_company_account(self):
        """Reset on a company-paid expense reverses the auto-generated move."""
        company_expense = self.create_expenses({"payment_mode": "company_account"})
        # Bypass approval gates — we're testing action_reset, not approval.
        company_expense.sudo().write({"approval_state": "approved"})
        self.post_expenses_with_wizard(
            company_expense, journal=self.company_data["default_journal_bank"]
        )
        self.assertTrue(company_expense.account_move_id)
        company_expense.action_reset()
        self.assertEqual(company_expense.state, "draft")

    def test_action_reset_blocked_on_hashed_journal(self):
        """Reset must fail when the linked move sits on a hash-locked journal."""
        journals = (
            self.company_data["default_journal_bank"]
            | self.company_data["default_journal_purchase"]
        )
        journals.write({"restrict_mode_hash_table": True})
        self.post_expenses_with_wizard(self.expense)
        wizard = self._get_payment_wizard()
        wizard.action_create_payments()
        with self.assertRaises(UserError):
            self.expense.action_reset()
