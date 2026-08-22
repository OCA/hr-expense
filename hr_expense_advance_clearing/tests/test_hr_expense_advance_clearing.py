# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpenseAdvanceClearing(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        advance_account = cls.company_data["default_account_deferred_expense"]
        advance_account.reconcile = True
        cls.emp_advance = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        cls.emp_advance.property_account_expense_id = advance_account
        cls.product_a.standard_price = 0

    def _new_advance(self, amount=1000.0):
        advance = self.env["hr.expense"].create(
            {
                "name": f"Advance {amount}",
                "employee_id": self.expense_employee.id,
                "product_id": self.emp_advance.id,
                "total_amount_currency": amount,
                "expense_type": "advance",
                "payment_mode": "own_account",
            }
        )
        advance.action_submit()
        if advance.state == "submitted":
            advance.action_approve()
        return advance

    def _new_clearing(self, advance, amount):
        return self.env["hr.expense"].create(
            {
                "name": f"Clearing {amount}",
                "employee_id": self.expense_employee.id,
                "product_id": self.product_a.id,
                "total_amount_currency": amount,
                "payment_mode": "own_account",
                "clearing_advance_id": advance.id,
            }
        )

    def test_advance_constraint_taxes_forbidden(self):
        """An advance expense cannot carry taxes."""
        tax = self.env["account.tax"].create(
            {"name": "T", "amount": 10.0, "type_tax_use": "purchase"}
        )
        advance = self.env["hr.expense"].create(
            {
                "name": "Advance",
                "employee_id": self.expense_employee.id,
                "product_id": self.emp_advance.id,
                "total_amount_currency": 100.0,
                "expense_type": "advance",
                "payment_mode": "own_account",
            }
        )
        with self.assertRaises(ValidationError):
            advance.tax_ids = [(6, 0, tax.ids)]

    def test_clearing_constraint_same_employee(self):
        """A clearing expense's advance must belong to the same employee."""
        advance = self._new_advance()
        # hr.employee creation requires resource.resource access in 19.0;
        # use sudo() since this test isn't exercising employee permissions.
        other_emp = self.env["hr.employee"].sudo().create({"name": "Other"})
        with self.assertRaises(ValidationError):
            self.env["hr.expense"].create(
                {
                    "name": "Mismatch",
                    "employee_id": other_emp.id,
                    "product_id": self.product_a.id,
                    "total_amount_currency": 50.0,
                    "clearing_advance_id": advance.id,
                }
            )

    def test_clearing_residual_tracks_drafts_vs_approved(self):
        """clearing_residual excludes draft/submitted/refused clearings;
        only approved+ clearings count."""
        advance = self._new_advance(1000.0)
        c_draft = self._new_clearing(advance, 300.0)
        self.assertEqual(c_draft.state, "draft")
        self.assertEqual(advance.cleared_amount, 0.0)
        self.assertEqual(advance.clearing_residual, 1000.0)
        c_draft.action_submit()
        if c_draft.state == "submitted":
            c_draft.action_approve()
        advance.invalidate_recordset(["cleared_amount", "clearing_residual"])
        self.assertEqual(advance.cleared_amount, 300.0)
        self.assertEqual(advance.clearing_residual, 700.0)

    def test_amount_payable_on_clearing(self):
        """A clearing expense's amount_payable = max(total − advance_residual, 0)."""
        advance = self._new_advance(1000.0)
        c_eq = self._new_clearing(advance, 1000.0)
        self.assertEqual(c_eq.amount_payable, 0.0)
        c_gt = self._new_clearing(advance, 1500.0)
        self.assertEqual(c_gt.amount_payable, 500.0)
        c_lt = self._new_clearing(advance, 500.0)
        self.assertEqual(c_lt.amount_payable, 0.0)

    def test_employee_advance_count(self):
        """advance_count + advance_expense_ids on hr.employee."""
        self.assertEqual(self.expense_employee.advance_count, 0)
        self._new_advance(500.0)
        self.expense_employee.invalidate_recordset(["advance_count"])
        self.assertEqual(self.expense_employee.advance_count, 1)

    def test_action_return_advance_guards(self):
        """action_return_advance gates on expense_type + residual, and
        returns the payment-register wizard action when valid."""
        advance = self._new_advance(500.0)
        self._post(advance)
        # A regular expense cannot be returned.
        regular = self.env["hr.expense"].create(
            {
                "name": "regular",
                "employee_id": self.expense_employee.id,
                "product_id": self.product_a.id,
                "total_amount_currency": 50.0,
                "payment_mode": "own_account",
            }
        )
        with self.assertRaises(UserError):
            regular.action_return_advance()
        # The advance has residual → action returns the wizard.
        self.assertGreater(advance.clearing_residual, 0)
        action = advance.action_return_advance()
        self.assertEqual(action["res_model"], "account.payment.register")
        self.assertEqual(action["context"]["default_advance_id"], advance.id)
        self.assertTrue(action["context"].get("hr_return_advance"))
        # The wizard is invoked on the advance's open move line (not on a bare
        # hr.expense), so the register-payment wizard accepts it.
        self.assertEqual(action["context"]["active_model"], "account.move.line")
        self.assertTrue(action["context"]["active_ids"])
        # Once fully cleared, residual is zero → action raises.
        clearing = self._new_clearing(advance, 500.0)
        clearing.action_submit()
        if clearing.state == "submitted":
            clearing.action_approve()
        advance.invalidate_recordset(["cleared_amount", "clearing_residual"])
        self.assertEqual(advance.clearing_residual, 0.0)
        with self.assertRaises(UserError):
            advance.action_return_advance()

    def test_return_advance_payment_carries_advance_id(self):
        """The payment created by Return Advance must carry advance_id.

        Core creates the payment inside _init_payments() under clean_context(),
        which drops every default_* key — so reading default_advance_id from the
        context at that point finds nothing. The wizard therefore holds it in a
        field, set at create() before the context is cleaned.
        """
        advance = self._new_advance(500.0)
        advance.action_submit()
        if advance.state == "submitted":
            advance.action_approve()
        self.post_expenses_with_wizard(advance)
        action = advance.action_return_advance()
        # Drive the wizard through Form, not create(). create() triggers the
        # precompute chain server-side and resolves journal/currency even when
        # the dialog cannot -- so an ORM-only test passes while the button is
        # broken for every user. Form replays default_get + onchange, which is
        # what the web client actually does.
        form = Form(
            self.env["account.payment.register"].with_context(**action["context"])
        )
        self.assertTrue(
            form.currency_id,
            "Return Advance must open with a currency; account.move requires it",
        )
        self.assertTrue(
            form.journal_id,
            "Return Advance must open with a journal",
        )
        wizard = form.save()
        self.assertEqual(
            wizard.advance_id,
            advance,
            "default_advance_id must land on the wizard field at create()",
        )
        payments = wizard._create_payments()
        self.assertEqual(
            payments.advance_id,
            advance,
            "advance_id must survive core's clean_context() on payment creation",
        )
        self.assertEqual(payments.currency_id, wizard.currency_id)
        advance.invalidate_recordset(["returned_amount", "clearing_residual"])
        self.assertIn(payments, advance.payment_return_ids)

    def test_clearing_fields_are_group_children(self):
        """The module's fields must sit directly in a <group>.

        Odoo only auto-renders a label for a direct <group> child. Core wraps
        product_id in an anonymous <div> with a separate <label for="product_id"/>,
        so anchoring on `product_id position="after"` drops the fields inside that
        div and they render with no label at all -- which is what 18.0's dedicated
        <group> avoided.
        """
        arch = etree.fromstring(
            self.env["hr.expense"].get_view(view_type="form")["arch"]
        )
        for fname in ("clearing_advance_id", "advance_residual", "clearing_residual"):
            nodes = arch.xpath(f"//field[@name='{fname}']")
            self.assertTrue(nodes, f"{fname} missing from the expense form")
            self.assertEqual(
                nodes[0].getparent().tag,
                "group",
                f"{fname} must be a <group> child or it renders without a label",
            )

    # -------------------------------------------------------------------------
    # Posting: clearing books as a journal entry against the advance
    # -------------------------------------------------------------------------

    def _post(self, expense):
        if expense.state == "draft":
            expense.action_submit()
        if expense.state == "submitted":
            expense.action_approve()
        self.post_expenses_with_wizard(expense)

    def test_clearing_posts_as_entry_and_reconciles(self):
        """A clearing expense posts as a journal entry (not a vendor receipt)
        crediting the advance account, reconciled against the advance."""
        account_advance = self.emp_advance.property_account_expense_id
        advance = self._new_advance(1000.0)
        self._post(advance)
        # The advance itself keeps core's vendor-receipt behaviour.
        self.assertEqual(advance.account_move_id.move_type, "in_receipt")
        clearing = self._new_clearing(advance, 600.0)
        self._post(clearing)
        move = clearing.account_move_id
        self.assertEqual(move.move_type, "entry")
        # Booked as a journal entry in a general journal, not a purchase bill.
        self.assertEqual(move.journal_id.type, "general")
        adv_lines = move.line_ids.filtered(
            lambda line: line.account_id == account_advance
        )
        self.assertAlmostEqual(sum(adv_lines.mapped("credit")), 600.0)
        self.assertTrue(
            all(adv_lines.mapped("reconciled")),
            "clearing entry's advance line must reconcile against the advance",
        )
        advance.invalidate_recordset(["cleared_amount", "clearing_residual"])
        self.assertAlmostEqual(advance.clearing_residual, 400.0)
        # The advance's own GL line is now partially reconciled: 600 of 1000
        # consumed, 400 still open.
        advance_gl = advance.account_move_id.line_ids.filtered(
            lambda line: line.account_id == account_advance
        )
        self.assertAlmostEqual(sum(advance_gl.mapped("amount_residual")), 400.0)

    def test_clearing_uses_configured_clearing_journal(self):
        """The company's clearing journal, when set, wins over the fallback."""
        clearing_journal = self.env["account.journal"].create(
            {
                "name": "Clearing Other",
                "code": "CLRO",
                "type": "general",
                "company_id": self.env.company.id,
            }
        )
        self.env.company.clearing_journal_id = clearing_journal
        advance = self._new_advance(500.0)
        self._post(advance)
        clearing = self._new_clearing(advance, 200.0)
        self._post(clearing)
        self.assertEqual(clearing.account_move_id.journal_id, clearing_journal)

    def test_clearing_over_advance_splits_to_payable(self):
        """When the clearing exceeds the advance, the excess books to the
        employee payable so it can still be reimbursed."""
        account_advance = self.emp_advance.property_account_expense_id
        payable = (
            self.expense_employee.sudo().work_contact_id.property_account_payable_id
        )
        advance = self._new_advance(1000.0)
        self._post(advance)
        clearing = self._new_clearing(advance, 1500.0)
        self._post(clearing)
        move = clearing.account_move_id
        self.assertEqual(move.move_type, "entry")
        self.assertAlmostEqual(
            sum(
                move.line_ids.filtered(
                    lambda line: line.account_id == account_advance
                ).mapped("credit")
            ),
            1000.0,
        )
        self.assertAlmostEqual(
            sum(
                move.line_ids.filtered(lambda line: line.account_id == payable).mapped(
                    "credit"
                )
            ),
            500.0,
        )
        advance.invalidate_recordset(["cleared_amount", "clearing_residual"])
        self.assertEqual(advance.clearing_residual, 0.0)
        # The leftover 500 stays open on the move as the amount still due to
        # the employee (drives amount_payable / Register Payment).
        self.assertAlmostEqual(move.amount_residual, 500.0)

    def test_multiple_clearings_group_into_one_entry(self):
        """Several clearings of the same advance posted together produce a
        single entry, each debiting its own expense line, jointly crediting
        the advance."""
        account_advance = self.emp_advance.property_account_expense_id
        advance = self._new_advance(1000.0)
        self._post(advance)
        c1 = self._new_clearing(advance, 300.0)
        c2 = self._new_clearing(advance, 250.0)
        expenses = c1 | c2
        for expense in expenses:
            expense.action_submit()
            if expense.state == "submitted":
                expense.action_approve()
        self.post_expenses_with_wizard(expenses)
        self.assertEqual(c1.account_move_id, c2.account_move_id)
        move = c1.account_move_id
        self.assertEqual(move.move_type, "entry")
        self.assertEqual(len(move.line_ids.expense_id), 2)
        self.assertAlmostEqual(
            sum(
                move.line_ids.filtered(
                    lambda line: line.account_id == account_advance
                ).mapped("credit")
            ),
            550.0,
        )
        advance.invalidate_recordset(["cleared_amount", "clearing_residual"])
        self.assertAlmostEqual(advance.clearing_residual, 450.0)

    def test_clearing_before_advance_posted_is_blocked(self):
        """A clearing cannot post while its advance is still unposted —
        otherwise its advance-account credit would dangle."""
        advance = self._new_advance(1000.0)  # approved but NOT posted
        clearing = self._new_clearing(advance, 200.0)
        with self.assertRaises(UserError):
            self._post(clearing)
