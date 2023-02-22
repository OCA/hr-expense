# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import Form, TransactionCase


class TestHrExpenseCancel(TransactionCase):
    def setUp(self):
        super().setUp()
        self.sheet_travel = self.env.ref("hr_expense.travel_ny_sheet")
        main_currency = self.env.company.currency_id
        self.sheet_travel.currency_id = main_currency.id
        self.sheet_travel.expense_line_ids.write({"currency_id": main_currency.id})

    def _get_payment_wizard(self, expense_sheet):
        action = expense_sheet.action_register_payment()
        ctx = action.get("context")
        f = Form(self.env["account.payment.register"].with_context(**ctx))
        register_payment = f.save()
        return register_payment

    def test_01_action_cancel_expense(self):
        self.sheet_travel.action_sheet_move_create()
        self.assertTrue(self.sheet_travel.account_move_id)
        self.assertEqual(self.sheet_travel.account_move_id.state, "posted")
        self.assertFalse(self.sheet_travel.account_move_id.payment_state)
        self.assertEqual(self.sheet_travel.state, "post")
        account_move = self.sheet_travel.account_move_id
        # Cancel Expense with standard odoo
        # Expense change state to draft, Journal Entries will reverse
        self.sheet_travel.action_unpost()
        self.assertFalse(self.sheet_travel.account_move_id)
        self.assertEqual(account_move.state, "posted")
        self.assertEqual(account_move.payment_state, "reversed")
        self.assertEqual(self.sheet_travel.state, "draft")

        # Config ex_cancel_policy change state to approved
        self.env.company.ex_cancel_policy = "approve"
        self.sheet_travel.action_submit_sheet()
        self.assertEqual(self.sheet_travel.state, "submit")
        self.sheet_travel.approve_expense_sheets()
        self.assertEqual(self.sheet_travel.state, "approve")
        self.sheet_travel.action_sheet_move_create()
        account_move = self.sheet_travel.account_move_id
        # Cancel Expense with set expense stage approve
        # Expense change state to approve, Journal Entries will reverse
        self.sheet_travel.action_unpost()
        self.assertFalse(self.sheet_travel.account_move_id)
        self.assertEqual(account_move.state, "posted")
        self.assertEqual(account_move.payment_state, "reversed")
        self.assertEqual(self.sheet_travel.state, "approve")

    def test_02_action_cancel_journal_entries(self):
        self.sheet_travel.action_sheet_move_create()
        self.assertTrue(self.sheet_travel.account_move_id)
        self.assertEqual(self.sheet_travel.account_move_id.state, "posted")
        self.assertFalse(self.sheet_travel.account_move_id.payment_state)
        self.assertEqual(self.sheet_travel.state, "post")
        # Cancel journal entries, expense change state to cancel with standard odoo
        self.sheet_travel.account_move_id.button_draft()
        self.sheet_travel.account_move_id.button_cancel()
        self.assertEqual(self.sheet_travel.state, "cancel")
        self.assertEqual(self.sheet_travel.account_move_id.state, "cancel")

        # Config je_cancel_policy change state to approved
        self.env.company.je_cancel_policy = "approve"
        self.sheet_travel.action_submit_sheet()
        self.assertEqual(self.sheet_travel.state, "submit")
        self.sheet_travel.approve_expense_sheets()
        self.assertEqual(self.sheet_travel.state, "approve")
        self.sheet_travel.action_sheet_move_create()
        # Cancel journal entries with set expense stage approve
        # Expense change state to approve, Journal Entries will cancel
        self.sheet_travel.account_move_id.button_draft()
        self.sheet_travel.account_move_id.button_cancel()
        self.assertEqual(self.sheet_travel.state, "approve")
        self.assertEqual(self.sheet_travel.account_move_id.state, "cancel")

    def test_03_action_cancel_payment_expense(self):
        self.sheet_travel.action_sheet_move_create()

        payment_wizard = self._get_payment_wizard(self.sheet_travel)
        payment_wizard.action_create_payments()
        self.assertEqual(self.sheet_travel.state, "done")
        self.assertTrue(self.sheet_travel.payment_ids)
        self.assertEqual(self.sheet_travel.payment_ids.state, "posted")
        # Cancel payment, expense change state to cancel with standard odoo
        self.sheet_travel.payment_ids.action_draft()
        self.sheet_travel.payment_ids.action_cancel()
        self.assertEqual(self.sheet_travel.state, "cancel")
        self.assertEqual(self.sheet_travel.payment_ids.state, "cancel")

        # Config payment_cancel_policy change state to posted
        self.env.company.payment_cancel_policy = "post"
        self.sheet_travel.action_submit_sheet()
        self.assertEqual(self.sheet_travel.state, "submit")
        self.sheet_travel.approve_expense_sheets()
        self.assertEqual(self.sheet_travel.state, "approve")
        self.sheet_travel.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard(self.sheet_travel)
        payment_wizard.action_create_payments()
        self.assertEqual(self.sheet_travel.state, "done")
        self.assertEqual(self.sheet_travel.payment_ids[0].state, "posted")
        # Cancel payment with set expense stage posted
        # Expense change state to posted, payment will cancel
        self.sheet_travel.payment_ids[0].action_draft()
        self.sheet_travel.payment_ids[0].action_cancel()
        self.assertEqual(self.sheet_travel.state, "post")
        self.assertEqual(self.sheet_travel.payment_ids[0].state, "cancel")
