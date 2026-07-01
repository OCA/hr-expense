# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form

from odoo.addons.base.tests.common import BaseCommon


class TestHrExpensePettyCash(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Object
        cls.account_obj = cls.env["account.account"]
        cls.journal_obj = cls.env["account.journal"]
        cls.petty_cash_obj = cls.env["petty.cash"]
        cls.move_obj = cls.env["account.move"]
        cls.sheet_obj = cls.env["hr.expense.sheet"]
        cls.exp_obj = cls.env["hr.expense"]

        # Demo data
        cls.employee_1 = cls.env.ref("hr.employee_admin")
        cls.employee_2 = cls.env.ref("hr.employee_al")
        cls.product = cls.env.ref("hr_expense.expense_product_travel_accommodation")
        cls.partner_1 = cls.env.ref("base.res_partner_1")
        cls.partner_2 = cls.env.ref("base.res_partner_2")
        cls.partner_3 = cls.env.ref("base.res_partner_3")

        cls.account_id = cls.account_obj.create(
            {
                "code": "111111",
                "name": "Payable - Test",
                "account_type": "liability_payable",
                "reconcile": True,
            }
        )
        cls.account_revenue_id = cls.account_obj.create(
            {
                "code": "111112",
                "name": "Cost Of Revenue - Test",
                "account_type": "expense_direct_cost",
            }
        )
        cls.petty_cash_journal_id = cls.journal_obj.create(
            {"code": "PC", "name": "Petty Cash", "type": "purchase"}
        )

        # Create a Petty Cash Account
        cls.petty_cash_account_id = cls.account_obj.create(
            {
                "code": "000000",
                "name": "Petty Cash - Test",
                "account_type": "asset_cash",
            }
        )
        cls.petty_cash_holder = cls._create_petty_cash_holder(cls, cls.partner_1)
        cls.petty_cash_holder_2 = cls._create_petty_cash_holder(cls, cls.partner_3)

        # Analytic setup, for testing analytic distribution on petty cash
        cls.analytic_plan = cls.env["account.analytic.plan"].create(
            {"name": "Petty Cash Plan - Test"}
        )
        cls.analytic_account = cls.env["account.analytic.account"].create(
            {
                "name": "Petty Cash Analytic - Test",
                "plan_id": cls.analytic_plan.id,
            }
        )
        # Tax setup (price-included) to test petty cash tax split.
        cls.tax_included = cls.env["account.tax"].create(
            {
                "name": "Petty Cash VAT 7% (included) - Test",
                "amount_type": "percent",
                "amount": 7.0,
                "price_include": True,
                "type_tax_use": "purchase",
                "company_id": cls.env.company.id,
            }
        )

    def _create_petty_cash_holder(self, partner):
        petty_cash_holder = self.petty_cash_obj.create(
            {
                "partner_id": partner.id,
                "account_id": self.petty_cash_account_id.id,
                "petty_cash_limit": 1000.0,
            }
        )
        return petty_cash_holder

    def _create_invoice(self, partner=False):
        invoice = self.move_obj.create(
            {
                "partner_id": partner,
                "move_type": "in_invoice",
                "invoice_date": fields.Date.today(),
            }
        )
        return invoice

    def _create_expense(
        self,
        amount,
        employee,
        payment_mode="own_account",
        petty_cash_holder=False,
        analytic_distribution=False,
        tax_ids=False,
    ):
        with Form(self.exp_obj) as expense:
            expense.name = "Expense - Test"
            expense.employee_id = employee
            expense.product_id = self.product
            expense.payment_mode = "own_account"  # temp bypass
        expense = expense.save()

        expense.total_amount = amount
        if tax_ids:
            expense.tax_ids = tax_ids
        else:
            expense.tax_ids = False  # no VAT
        if analytic_distribution:
            expense.analytic_distribution = analytic_distribution

        if payment_mode == "petty_cash":
            expense.payment_mode = "petty_cash"
            expense.petty_cash_id = petty_cash_holder

        return expense

    def _create_expense_sheet(self, expenses):
        expense_sheet = self.sheet_obj.create(
            {
                "name": expenses[0].name,
                "employee_id": expenses[0].employee_id.id,
                "expense_line_ids": [Command.set(expenses.ids)],
            }
        )
        return expense_sheet

    def _create_multi_invoice_line(self, petty_cash=False):
        invoice = self.move_obj.create(
            {
                "partner_id": self.partner_1.id,
                "move_type": "in_invoice",
                "invoice_date": fields.Date.today(),
                "is_petty_cash": petty_cash,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line 1",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": self.account_revenue_id.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "Test line 2",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": self.account_revenue_id.id,
                        }
                    ),
                ],
            }
        )
        return invoice

    def _check_warning(self):
        # no partner and check petty cash
        invoice = self._create_invoice()
        with self.assertRaises(ValidationError):
            invoice.is_petty_cash = True
            invoice._onchange_is_petty_cash()
        # partner is not holder.
        invoice = self._create_invoice(self.partner_2.id)
        with self.assertRaises(ValidationError):
            invoice.is_petty_cash = True
            invoice._onchange_is_petty_cash()
        invoice = self._create_invoice(self.partner_1.id)
        invoice.is_petty_cash = True
        invoice._onchange_is_petty_cash()

        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids.price_unit, 1000.0)

        # over limit
        with self.assertRaises(ValidationError):
            invoice.invoice_line_ids.with_context(check_move_validity=False).write(
                {"price_unit": 1500.0}
            )
            invoice.action_post()

        # change account to not petty cash
        invoice.invoice_line_ids.account_id = self.account_revenue_id.id
        with self.assertRaises(UserError):
            invoice.action_post()

        # no partner
        invoice.invoice_line_ids.account_id = self.petty_cash_account_id.id
        with self.assertRaises(UserError):
            invoice.write({"partner_id": False})
            invoice.action_post()

        # Create line manual and not check petty cash
        invoice = self.move_obj.create(
            {
                "partner_id": self.partner_1.id,
                "move_type": "in_invoice",
                "invoice_date": fields.Date.today(),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Test line",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": self.account_revenue_id.id,
                        },
                    )
                ],
            }
        )
        invoice.invoice_line_ids.account_id = self.petty_cash_account_id.id
        with self.assertRaises(UserError):
            invoice.action_post()

        # Create multi line and check petty cash
        with self.assertRaises(UserError):
            self._create_multi_invoice_line(petty_cash=True)

    def test_01_create_petty_cash_holder(self):
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 0.00)
        self._check_warning()
        invoice = self._create_invoice(self.partner_1.id)
        invoice.is_petty_cash = True
        invoice._onchange_is_petty_cash()
        invoice.action_post()
        self.petty_cash_holder._compute_petty_cash_balance()
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 1000.0)

    def test_02_create_expense_petty_cash(self):
        invoice = self._create_invoice(self.partner_1.id)
        invoice.is_petty_cash = True
        invoice._onchange_is_petty_cash()
        invoice.invoice_line_ids.price_unit = 1000.0
        invoice.action_post()
        self.petty_cash_holder._compute_petty_cash_balance()
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 1000.0)
        # Create expense
        expense_own = self._create_expense(400.0, self.employee_1, "own_account")
        expense_petty_cash = self._create_expense(
            400.0, self.employee_1, "petty_cash", self.petty_cash_holder
        )
        expense_petty_cash_2 = self._create_expense(
            200.0, self.employee_1, "petty_cash", self.petty_cash_holder_2
        )
        expense_report = expense_own + expense_petty_cash + expense_petty_cash_2
        # Check expenses must have 1 petty cash holder only
        with self.assertRaises(ValidationError):
            expense_report.action_submit_expenses()
        # check create direct expense sheet and many diff petty cash
        expense_diff_holder = expense_petty_cash + expense_petty_cash_2
        with self.assertRaises(ValidationError):
            self._create_expense_sheet(expense_diff_holder)
        # create expense normal not petty cash
        expense_own.sheet_id = False
        action = expense_own.action_submit_expenses()
        self.assertEqual(action["res_model"], "hr.expense.sheet")
        sheet = self._create_expense_sheet(expense_petty_cash)
        self.assertEqual(sheet.state, "draft")
        with self.assertRaises(ValidationError):
            sheet.expense_line_ids.total_amount = 1600.0
            sheet._check_petty_cash_amount()
        sheet.expense_line_ids.total_amount = 400.0
        # Submitted to Manager and Approve
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.action_approve_expense_sheets()
        self.assertEqual(sheet.state, "done")
        self.assertTrue(sheet.account_move_ids.id)
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 600.0)

        # Check action
        action = sheet.action_open_account_moves()
        self.assertEqual(len(sheet.account_move_ids), 1)
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(action["res_id"], sheet.account_move_ids.id)

    def test_03_create_expense_petty_cash_with_journal(self):
        self.petty_cash_holder.journal_id = self.petty_cash_journal_id
        invoice = self._create_invoice(self.partner_1.id)
        invoice.is_petty_cash = True
        invoice._onchange_is_petty_cash()
        invoice.invoice_line_ids.price_unit = 1000.0
        self.assertEqual(invoice.journal_id, self.petty_cash_holder.journal_id)
        invoice.action_post()
        self.petty_cash_holder._compute_petty_cash_balance()
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 1000.0)
        expense_petty_cash = self._create_expense(
            400.0, self.employee_1, "petty_cash", self.petty_cash_holder
        )
        expense_petty_cash.action_submit_expenses()
        sheet = self._create_expense_sheet(expense_petty_cash)
        self.assertEqual(sheet.journal_id, self.petty_cash_holder.journal_id)

    def test_04_change_partner_bill_not_petty_cash(self):
        """Test change partner on bills without petty cash,
        line should not be reset.
        """
        invoice = self._create_multi_invoice_line()

        invoice.partner_id = self.partner_2
        invoice._onchange_is_petty_cash()

        self.assertEqual(len(invoice.invoice_line_ids), 2)
        self.assertEqual(
            set(invoice.invoice_line_ids.mapped("name")),
            {"Test line 1", "Test line 2"},
        )

    def test_05_petty_cash_with_analytic_and_tax(self):
        """Petty cash entry must carry analytic on the expense side and split
        the included tax into proper base + tax lines while the clearing side
        keeps the total amount paid."""
        # Fund the petty cash holder first.
        self.petty_cash_holder.petty_cash_limit = 2000.0
        invoice = self._create_invoice(self.partner_1.id)
        invoice.is_petty_cash = True
        invoice._onchange_is_petty_cash()
        invoice.invoice_line_ids.price_unit = 2000.0
        invoice.action_post()
        self.petty_cash_holder._compute_petty_cash_balance()
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 2000.0)

        # Expense 1070 (tax-included) -> base 1000 + 7% VAT 70.
        expense = self._create_expense(
            1070.0,
            self.employee_1,
            "petty_cash",
            self.petty_cash_holder,
            analytic_distribution={str(self.analytic_account.id): 100},
            tax_ids=self.tax_included,
        )
        expense.action_submit_expenses()
        sheet = self._create_expense_sheet(expense)
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        # Petty cash sheets are paid automatically upon approval.
        self.assertEqual(sheet.state, "done")
        self.assertEqual(sheet.payment_state, "paid")

        move = sheet.account_move_ids
        self.assertEqual(move.move_type, "entry")

        # Expense base line carries the analytic distribution.
        base_line = move.line_ids.filtered(
            lambda line: not line.tax_line_id
            and line.account_id != self.petty_cash_account_id
        )
        self.assertEqual(len(base_line), 1)
        self.assertEqual(
            base_line.analytic_distribution,
            {str(self.analytic_account.id): 100},
        )
        # Clearing side carries no analytic distribution.
        petty_cash_line = move.line_ids.filtered(
            lambda line: line.account_id == self.petty_cash_account_id
        )
        self.assertEqual(len(petty_cash_line), 1)
        self.assertFalse(petty_cash_line.analytic_distribution)
        # Clearing side reflects the full tax-included amount paid.
        self.assertEqual(sum(petty_cash_line.mapped("credit")), 1070.0)
        # The move must be balanced.
        self.assertEqual(sum(move.line_ids.mapped("debit")), 1070.0)
        self.assertEqual(sum(move.line_ids.mapped("credit")), 1070.0)
        # A tax line must have been generated.
        tax_lines = move.line_ids.filtered(lambda line: line.tax_line_id)
        self.assertTrue(
            tax_lines,
            "Petty cash entry should generate a tax line.",
        )

        # Resetting the move to draft must not create a spurious
        # "Automatic Balancing Line" and must keep the same line count.
        line_count = len(move.line_ids)
        move.button_draft()
        self.assertEqual(len(move.line_ids), line_count)
        self.assertFalse(
            move.line_ids.filtered(lambda line: line.name == "Automatic Balancing Line")
        )
        self.assertEqual(sheet.state, "approve")
        # Re-posting the move marks the petty cash sheet done/paid again
        # without creating any extra line.
        move.action_post()
        self.assertEqual(move.state, "posted")
        self.assertEqual(len(move.line_ids), line_count)
        self.assertEqual(sheet.state, "done")
        self.assertEqual(sheet.payment_state, "paid")
