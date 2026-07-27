# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import importlib.util
from pathlib import Path

from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


def _load_post_migration():
    """Import the 19.0.1.0.0 upgrade script by path (not an importable module)."""
    path = Path(__file__).parents[1] / "migrations" / "19.0.1.0.0" / "post-migration.py"
    spec = importlib.util.spec_from_file_location("hr_expense_payment_post_mig", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged("-at_install", "post_install")
class TestHrExpensePayment(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Build an employee-paid expense, submit + approve + post (= receipt).
        cls.expense = cls.create_expenses({"payment_mode": "own_account"})
        cls.expense.action_submit()
        cls.expense.action_approve()
        cls.post_expenses_with_wizard(cls.expense)

    def _get_payment_wizard(self, expenses, amount=None):
        action = expenses.action_pay()
        wizard_form = Form(
            self.env[action["res_model"]].with_context(**action["context"])
        )
        wizard_form.journal_id = self.company_data["default_journal_bank"]
        if amount is not None:
            wizard_form.amount = amount
        return wizard_form.save()

    def test_core_expense_ids_field_not_overridden(self):
        """The module must not redefine core's account.payment.expense_ids
        (related to move_id.expense_ids)."""
        field = self.env["account.payment"]._fields["expense_ids"]
        self.assertEqual(field.type, "one2many")
        self.assertEqual(field.related, "move_id.expense_ids")

    def test_action_pay_links_payment_back_to_expense(self):
        """Registering payment from the expense links both directions."""
        self.assertFalse(self.expense.payment_ids)
        wizard = self._get_payment_wizard(self.expense)
        wizard.action_create_payments()
        self.assertEqual(len(self.expense.payment_ids), 1)
        payment = self.expense.payment_ids
        self.assertIn(self.expense, payment.reconciled_expense_ids)
        # Core's related field stays empty for reimbursement payments.
        self.assertFalse(payment.expense_ids)

    def test_partial_payment_links(self):
        """Partially reconciled payments are linked too."""
        wizard = self._get_payment_wizard(
            self.expense, amount=self.expense.total_amount / 2
        )
        wizard.action_create_payments()
        self.assertEqual(len(self.expense.payment_ids), 1)
        self.assertIn(self.expense, self.expense.payment_ids.reconciled_expense_ids)
        # Pay the remainder: both payments end up linked.
        wizard = self._get_payment_wizard(self.expense)
        wizard.action_create_payments()
        self.assertEqual(len(self.expense.payment_ids), 2)

    def test_grouped_payment_links_all_expenses(self):
        """One grouped payment for several expenses back-links to all."""
        expense_2 = self.create_expenses(
            {"payment_mode": "own_account", "total_amount_currency": 123.0}
        )
        expense_2.action_submit()
        expense_2.action_approve()
        self.post_expenses_with_wizard(expense_2)
        expenses = self.expense | expense_2
        action = expenses.action_pay()
        wizard = (
            self.env[action["res_model"]]
            .with_context(**action["context"])
            .create({"group_payment": True})
        )
        wizard.action_create_payments()
        payment = self.expense.payment_ids
        self.assertEqual(len(payment), 1)
        self.assertEqual(expense_2.payment_ids, payment)
        self.assertEqual(payment.reconciled_expense_ids, expenses)

    def test_unreconcile_keeps_wizard_link(self):
        """Wizard-registered payments stay linked after unreconciling, via
        core's stored matched_payment_ids (reconciled_payment_ids semantics)."""
        wizard = self._get_payment_wizard(self.expense)
        wizard.action_create_payments()
        payment = self.expense.payment_ids
        self.expense.account_move_id.line_ids.remove_move_reconcile()
        self.assertEqual(self.expense.payment_ids, payment)
        self.assertIn(self.expense, payment.reconciled_expense_ids)

    def test_manual_reconcile_link_follows_reconciliation(self):
        """A manually created and reconciled payment links through the
        reconciliation only, so unreconciling dissolves it."""
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.expense.employee_id.work_contact_id.id,
                "amount": self.expense.total_amount,
                "journal_id": self.company_data["default_journal_bank"].id,
                # An outstanding account so the payment generates a move.
                "payment_method_line_id": self.outbound_payment_method_line.id,
            }
        )
        payment.action_post()
        self.assertTrue(payment.move_id)
        self.assertFalse(self.expense.payment_ids)
        lines = (
            payment.move_id.line_ids + self.expense.account_move_id.line_ids
        ).filtered(
            lambda line: line.account_id.account_type == "liability_payable"
            and not line.reconciled
        )
        lines.reconcile()
        self.assertEqual(self.expense.payment_ids, payment)
        self.assertIn(self.expense, payment.reconciled_expense_ids)
        self.expense.account_move_id.line_ids.remove_move_reconcile()
        self.assertFalse(self.expense.payment_ids)
        self.assertFalse(payment.reconciled_expense_ids)

    def test_migration_carries_legacy_sheet_links(self):
        """The upgrade script carries a legacy link whose reconciliation no
        longer exists onto the expense's entry, idempotently."""
        payment = self.env["account.payment"].create(
            {
                "payment_type": "outbound",
                "partner_type": "supplier",
                "partner_id": self.expense.employee_id.work_contact_id.id,
                "amount": self.expense.total_amount,
                "journal_id": self.company_data["default_journal_bank"].id,
                "payment_method_line_id": self.outbound_payment_method_line.id,
            }
        )
        payment.action_post()
        # Nothing ties the two together today.
        self.assertFalse(self.expense.payment_ids)
        legacy_sheet_id = 4242
        self.expense.former_sheet_id = legacy_sheet_id
        self.expense.flush_recordset()
        self.env.cr.execute(
            """
            CREATE TABLE payment_expense_sheet_rel (
                payment_id integer NOT NULL,
                sheet_id integer NOT NULL,
                PRIMARY KEY (payment_id, sheet_id)
            );
            INSERT INTO payment_expense_sheet_rel VALUES (%s, %s);
            """,
            (payment.id, legacy_sheet_id),
        )
        post_migration = _load_post_migration()
        post_migration.migrate(self.env.cr, "19.0.1.0.0")
        self.env.invalidate_all()
        self.assertEqual(self.expense.payment_ids, payment)
        self.assertIn(self.expense, payment.reconciled_expense_ids)
        # Running it again does not duplicate the link.
        post_migration.migrate(self.env.cr, "19.0.1.0.0")
        self.env.invalidate_all()
        self.assertEqual(self.expense.payment_ids, payment)

    def test_migration_is_a_noop_without_the_legacy_table(self):
        """On a fresh 19.0 install the script does nothing and does not fail."""
        post_migration = _load_post_migration()
        post_migration.migrate(self.env.cr, "19.0.1.0.0")
        self.assertFalse(self.expense.payment_ids)

    def test_migration_noops_when_former_sheet_id_unfilled(self):
        """Unfilled legacy pointer: warn and carry nothing."""
        self.env.cr.execute(
            """
            CREATE TABLE payment_expense_sheet_rel (
                payment_id integer NOT NULL,
                sheet_id integer NOT NULL
            );
            INSERT INTO payment_expense_sheet_rel VALUES (1, 4242);
            """
        )
        post_migration = _load_post_migration()
        with self.assertLogs(level="WARNING") as capture:
            post_migration.migrate(self.env.cr, "19.0.1.0.0")
        self.assertTrue(any("unfilled" in line for line in capture.output))
        self.assertFalse(self.expense.payment_ids)

    def test_search_payment_ids(self):
        """Both computed fields are searchable."""
        wizard = self._get_payment_wizard(self.expense)
        wizard.action_create_payments()
        payment = self.expense.payment_ids
        found_expenses = self.env["hr.expense"].search(
            [("payment_ids", "in", payment.ids)]
        )
        self.assertEqual(found_expenses, self.expense)
        found_payments = self.env["account.payment"].search(
            [("reconciled_expense_ids", "in", self.expense.ids)]
        )
        self.assertEqual(found_payments, payment)

    def test_payment_ids_readable_by_employee(self):
        """Employees without accounting access can read the computed link."""
        wizard = self._get_payment_wizard(self.expense)
        wizard.action_create_payments()
        expense = self.expense.with_user(self.expense_user_employee)
        self.assertEqual(len(expense.payment_ids), 1)

    def test_company_paid_expense_not_linked(self):
        """Company-paid expenses stay core-only; module fields stay empty."""
        expense = self.create_expenses(
            {"payment_mode": "company_account", "total_amount_currency": 200.0}
        )
        expense.action_submit()
        expense.action_approve()
        expense.action_post()
        self.assertFalse(expense.payment_ids)
        payment = expense.account_move_id.origin_payment_id
        if payment:
            self.assertFalse(payment.reconciled_expense_ids)
            self.assertIn(expense, payment.expense_ids)
