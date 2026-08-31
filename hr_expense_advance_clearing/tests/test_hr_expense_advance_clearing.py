# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# Copyright 2024 Tecnativa - Víctor Martínez
# Copyright 2026 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpenseAdvanceClearing(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.advance_account = cls.company_data["default_account_deferred_expense"]
        cls.advance_account.reconcile = True

        cls.advance_product = cls.env.ref(
            "hr_expense_advance_clearing.product_emp_advance"
        )
        cls.advance_product.write(
            {
                "property_account_expense_id": cls.advance_account.id,
                "supplier_taxes_id": [Command.clear()],
            }
        )
        cls.product_a.standard_price = 0

        cls.clearing_journal = cls.env["account.journal"].create(
            {
                "name": "Advance Clearing",
                "code": "ACLR",
                "type": "general",
                "company_id": cls.company_data["company"].id,
            }
        )
        cls.company_data["company"].clearing_journal_id = cls.clearing_journal

    @classmethod
    def _create_expense(
        cls,
        name,
        amount,
        *,
        product=None,
        advance=False,
        advance_id=None,
        payment_mode="own_account",
        taxes=None,
    ):
        product = product or cls.product_a
        values = {
            "name": name,
            "employee_id": cls.expense_employee.id,
            "company_id": cls.company_data["company"].id,
            "currency_id": cls.company_data["currency"].id,
            "date": cls.frozen_today.date(),
            "product_id": product.id,
            "total_amount_currency": amount,
            "payment_mode": payment_mode,
            "advance": advance,
            "advance_id": advance_id and advance_id.id,
            "tax_ids": [Command.set((taxes or cls.env["account.tax"]).ids)],
        }
        if advance:
            values["account_id"] = cls.advance_account.id
        return cls.env["hr.expense"].create(values)

    @classmethod
    def _create_advance(cls, amount=1000.0, name="Advance 1,000"):
        return cls._create_expense(
            name,
            amount,
            product=cls.advance_product,
            advance=True,
        )

    @classmethod
    def _create_clearing(cls, advance, amount, name="Advance Clearing", taxes=None):
        return cls._create_expense(
            name,
            amount,
            advance_id=advance,
            taxes=taxes,
        )

    def _assert_tax_move(self, move, tax):
        tax_lines = move.line_ids.filtered(lambda line: line.tax_line_id == tax)
        self.assertTrue(tax_lines)
        self.assertAlmostEqual(sum(move.line_ids.mapped("balance")), 0.0)

    def _submit_approve(self, expense):
        expense.action_submit()
        self.assertEqual(expense.state, "submitted")
        expense.action_approve()
        self.assertEqual(expense.state, "approved")

    def _post_expense(self, expense, journal=None):
        self._submit_approve(expense)
        action = expense.action_post()
        wizard = (
            self.env["hr.expense.post.wizard"]
            .with_context(**action["context"])
            .browse(action["res_id"])
        )
        wizard.accounting_date = fields.Date.context_today(expense)
        if expense.advance_id:
            wizard.clearing_journal_id = journal or self.clearing_journal
        elif journal:
            wizard.employee_journal_id = journal
        wizard.action_post_entry()
        self.assertEqual(expense.account_move_id.state, "posted")
        return expense.account_move_id

    def _create_payment_from_action(self, action, amount):
        payment_register = self.env["account.payment.register"].with_context(
            **action["context"]
        )
        with Form(payment_register) as payment_form:
            payment_form.journal_id = self.company_data["default_journal_bank"]
            payment_form.payment_date = fields.Date.context_today(self.env.user)
            payment_form.amount = amount
        return payment_form.save()._create_payments()

    def _reconcile_payment_liquidity(self, payment):
        liquidity_lines = payment._seek_for_lines()[0]
        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.company_data["default_journal_bank"].id,
                "payment_ref": payment.name,
                "amount": (
                    payment.amount
                    if payment.payment_type == "inbound"
                    else -payment.amount
                ),
                "partner_id": payment.partner_id.id,
            }
        )
        suspense_lines = statement_line.with_context(
            skip_account_move_synchronization=True
        )._seek_for_lines()[1]
        suspense_lines.account_id = liquidity_lines.account_id
        (suspense_lines + liquidity_lines).reconcile()

    def _pay_expense(self, expense, amount, reconcile_bank=False):
        payment = self._create_payment_from_action(expense.action_pay(), amount)
        if reconcile_bank:
            self._reconcile_payment_liquidity(payment)
        return payment

    def _post_and_pay_advance(self, amount=1000.0, name="Advance 1,000"):
        advance = self._create_advance(amount, name)
        self._post_expense(advance)
        self.assertEqual(advance.clearing_residual, amount)
        self._pay_expense(advance, amount, reconcile_bank=True)
        self.assertEqual(advance.state, "paid")
        return advance

    def test_01_advance_constraints(self):
        advance = self._create_advance()
        with self.assertRaises(ValidationError):
            advance.advance_id = advance

        with self.assertRaises(ValidationError):
            self._create_expense(
                "Invalid advance product",
                100.0,
                product=self.product_a,
                advance=True,
            )

        with self.assertRaises(ValidationError):
            self._create_expense(
                "Company-paid advance",
                100.0,
                product=self.advance_product,
                advance=True,
                payment_mode="company_account",
            )

        with self.assertRaises(ValidationError):
            self._create_expense(
                "Taxed advance",
                100.0,
                product=self.advance_product,
                advance=True,
                taxes=self.tax_purchase_a,
            )

        self.advance_product.property_account_expense_id = False
        try:
            with self.assertRaises(ValidationError):
                self._create_advance(100.0, "Advance without account")
        finally:
            self.advance_product.property_account_expense_id = self.advance_account

    def test_02_clear_equal_advance(self):
        advance = self._post_and_pay_advance()
        open_action = advance.open_clear_advance()
        self.assertEqual(open_action["context"]["default_advance_id"], advance.id)
        self.assertEqual(
            open_action["context"]["default_employee_id"],
            self.expense_employee.id,
        )

        clearing = self._create_clearing(advance, 1000.0, "Clearing 1,000")
        self.assertEqual(clearing.advance_residual, 1000.0)
        clearing_move = self._post_expense(clearing)

        self.assertEqual(clearing.state, "paid")
        self.assertEqual(clearing_move.move_type, "entry")
        self.assertEqual(clearing_move.journal_id, self.clearing_journal)
        self.assertEqual(advance.clearing_residual, 0.0)
        self.assertEqual(clearing.amount_to_pay, 0.0)

        next_clearing = self._create_clearing(
            advance,
            100.0,
            "Clearing after advance is fully cleared",
        )
        next_clearing.action_submit()
        with self.assertRaises(ValidationError):
            next_clearing.action_approve()

        self.assertEqual(advance.clearing_count, 2)
        clearing_action = advance.action_open_clearings()
        self.assertEqual(
            set(clearing_action["domain"][0][2]),
            set(advance.clearing_ids.ids),
        )

        self.assertEqual(self.expense_employee.advance_count, 1)
        employee_action = self.expense_employee.action_open_advance_clearing()
        self.assertEqual(employee_action["domain"][0][2], advance.ids)

    def test_03_clear_more_than_advance_and_pay_difference(self):
        advance = self._post_and_pay_advance()
        tax = self.tax_purchase_a.copy(
            {"name": "Clearing tax excluded", "price_include": False}
        )
        clearing = self._create_clearing(
            advance,
            1200.0,
            "Clearing 1,200",
            taxes=tax,
        )

        self.assertEqual(clearing.advance_residual, 1000.0)
        self.assertEqual(clearing.amount_to_pay, 200.0)
        clearing_move = self._post_expense(clearing)

        self.assertEqual(clearing.state, "posted")
        self.assertEqual(clearing_move.move_type, "entry")
        self.assertEqual(clearing_move.journal_id, self.clearing_journal)
        self.assertEqual(clearing.amount_to_pay, 200.0)
        self.assertEqual(advance.clearing_residual, 0.0)
        self._assert_tax_move(clearing_move, tax)

        payment_action = clearing.action_pay()
        self.assertEqual(payment_action["context"]["active_model"], "account.move.line")
        self._create_payment_from_action(payment_action, 200.0)
        self.assertEqual(clearing.state, "paid")
        self.assertEqual(clearing.amount_to_pay, 0.0)

    def test_04_clear_less_than_advance_and_return_remaining(self):
        advance = self._post_and_pay_advance()
        tax = self.tax_purchase_a.copy(
            {"name": "Clearing tax included", "price_include": True}
        )
        clearing = self._create_clearing(
            advance,
            800.0,
            "Clearing 800",
            taxes=tax,
        )
        clearing_move = self._post_expense(clearing)

        self.assertEqual(clearing.state, "paid")
        self.assertEqual(advance.clearing_residual, 200.0)
        self._assert_tax_move(clearing_move, tax)

        return_action = advance.action_return_advance()
        with self.assertRaises(UserError):
            self._create_payment_from_action(return_action, 300.0)

        return_payment = self._create_payment_from_action(
            advance.action_return_advance(),
            200.0,
        )
        self.assertEqual(return_payment.payment_type, "inbound")
        self.assertEqual(return_payment.advance_id, advance)
        self.assertEqual(advance.clearing_residual, 0.0)
        self.assertEqual(advance.return_count, 1)

        payment_action = advance.action_open_payment_return()
        self.assertEqual(payment_action["domain"][0][2], return_payment.ids)
        with self.assertRaises(ValidationError):
            advance.action_return_advance()

    def test_05_clearing_product_defaults(self):
        advance = self._create_advance()
        advance.clearing_product_id = self.product_a

        action = advance.open_clear_advance()
        context = action["context"]
        self.assertFalse(context["default_advance"])
        self.assertEqual(context["default_advance_id"], advance.id)
        self.assertEqual(context["default_product_id"], self.product_a.id)
        self.assertEqual(context["default_name"], self.product_a.display_name)
        self.assertEqual(context["default_payment_mode"], "own_account")

        clearing = self.env["hr.expense"].new({"advance_id": advance.id})
        clearing._onchange_advance_id()
        self.assertEqual(clearing.product_id, self.product_a)
        self.assertEqual(clearing.name, self.product_a.display_name)

    def test_06_clearing_post_requires_miscellaneous_journal(self):
        advance = self._post_and_pay_advance()
        clearing = self._create_clearing(advance, 500.0, "Clearing without journal")
        self._submit_approve(clearing)

        self.company_data["company"].clearing_journal_id = False
        action = clearing.action_post()
        wizard = (
            self.env["hr.expense.post.wizard"]
            .with_context(**action["context"])
            .browse(action["res_id"])
        )
        self.assertTrue(wizard.is_advance_clearing)
        self.assertFalse(wizard.clearing_journal_id)
        with self.assertRaises(UserError):
            wizard.action_post_entry()

        wizard.clearing_journal_id = self.company_data["default_journal_purchase"]
        with self.assertRaises(ValidationError):
            wizard.action_post_entry()
