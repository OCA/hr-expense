# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form, TransactionCase


class TestHrExpensePettyCash(TransactionCase):
    def setUp(self):
        super(TestHrExpensePettyCash, self).setUp()

        self.employee_1 = self.env.ref("hr.employee_admin")
        self.employee_2 = self.env.ref("hr.employee_al")
        self.product_id = self.env.ref("hr_expense.air_ticket")
        self.partner_1 = self.env.ref("base.res_partner_1")
        self.partner_2 = self.env.ref("base.res_partner_2")
        self.partner_3 = self.env.ref("base.res_partner_3")
        self.payable_type = self.env.ref("account.data_account_type_payable")
        self.liquidity_type = self.env.ref("account.data_account_type_liquidity")
        self.cost_type = self.env.ref("account.data_account_type_direct_costs")
        self.account_id = self.env["account.account"].create(
            {
                "code": "111111",
                "name": "Payable - Test",
                "user_type_id": self.payable_type.id,
                "reconcile": True,
            }
        )
        self.account_revenue_id = self.env["account.account"].create(
            {
                "code": "111112",
                "name": "Cost Of Revenue - Test",
                "user_type_id": self.cost_type.id,
            }
        )
        self.petty_cash_journal_id = self.env["account.journal"].create(
            {"code": "PC", "name": "Petty Cash", "type": "general"}
        )

        # Create a Petty Cash Account
        self.petty_cash_account_id = self.env["account.account"].create(
            {
                "code": "000000",
                "name": "Petty Cash - Test",
                "user_type_id": self.liquidity_type.id,
            }
        )
        self.petty_cash_holder = self._create_petty_cash_holder(self.partner_1)
        self.petty_cash_holder_2 = self._create_petty_cash_holder(self.partner_3)

    def _create_petty_cash_holder(self, partner):
        petty_cash_holder = self.env["petty.cash"].create(
            {
                "partner_id": partner.id,
                "account_id": self.petty_cash_account_id.id,
                "petty_cash_limit": 1000.0,
            }
        )
        return petty_cash_holder

    def _create_invoice(self, partner=False):
        invoice = self.env["account.move"].create(
            {"partner_id": partner, "type": "in_invoice"}
        )
        return invoice

    def _create_expense(self, amount, employee_id, mode, petty_cash_holder=False):
        expense = self.env["hr.expense"].create(
            {
                "name": "Expense - Test",
                "employee_id": employee_id,
                "product_id": self.product_id.id,
                "unit_amount": amount,
                "payment_mode": mode,
                "petty_cash_id": petty_cash_holder,
            }
        )
        return expense

    def _create_expense_sheet(self, expenses):
        expense_sheet = (
            self.env["hr.expense.sheet"]
            .with_context({"default_petty_cash_id": self.petty_cash_holder.id})
            .create(
                {
                    "name": expenses[0].name,
                    "employee_id": expenses[0].employee_id.id,
                    "expense_line_ids": [(6, 0, expenses.ids)],
                }
            )
        )
        return expense_sheet

    def _create_multi_invoice_line(self, petty_cash=False):
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_1.id,
                "type": "in_invoice",
                "is_petty_cash": petty_cash,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Test line 1",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": self.account_revenue_id.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "Test line 2",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": self.account_revenue_id.id,
                        },
                    ),
                ],
            }
        )
        return invoice

    def _check_warning(self):
        # no partner and check petty cash
        invoice = self._create_invoice()
        with self.assertRaises(ValidationError):
            with Form(invoice) as inv:
                inv.is_petty_cash = True
        # partner is not holder.
        invoice = self._create_invoice(self.partner_2.id)
        with self.assertRaises(ValidationError):
            with Form(invoice) as inv:
                inv.is_petty_cash = True
        invoice = self._create_invoice(self.partner_1.id)
        with Form(invoice) as inv:
            inv.is_petty_cash = True
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertEqual(invoice.invoice_line_ids.price_unit, 1000.0)
        # over limit
        with self.assertRaises(ValidationError):
            invoice.invoice_line_ids.with_context({"check_move_validity": False}).write(
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
        invoice = self.env["account.move"].create(
            {
                "partner_id": self.partner_1.id,
                "type": "in_invoice",
                "invoice_line_ids": [
                    (
                        0,
                        0,
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
        with Form(invoice) as inv:
            inv.is_petty_cash = True
        invoice.action_post()
        self.petty_cash_holder._compute_petty_cash_balance()
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 1000.0)

    def test_02_create_expense_petty_cash(self):
        invoice = self._create_invoice(self.partner_1.id)
        with Form(invoice) as inv:
            inv.is_petty_cash = True
            inv.invoice_line_ids.price_unit = 1000.0
        invoice.action_post()
        self.petty_cash_holder._compute_petty_cash_balance()
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 1000.0)
        # Create expense
        expense_own = self._create_expense(400.0, self.employee_1.id, "own_account")
        expense_petty_cash = self._create_expense(
            400.0, self.employee_1.id, "petty_cash", self.petty_cash_holder.id
        )
        expense_petty_cash_2 = self._create_expense(
            200.0, self.employee_1.id, "petty_cash", self.petty_cash_holder_2.id
        )
        expense_petty_cash_3 = self._create_expense(
            100.0, self.employee_2.id, "petty_cash", self.petty_cash_holder_2.id
        )
        expense_report = expense_own + expense_petty_cash + expense_petty_cash_2
        with self.assertRaises(UserError):
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
            sheet.expense_line_ids.unit_amount = 1600.0
            sheet._check_petty_cash_amount()
        sheet.expense_line_ids.unit_amount = 400.0
        # Submitted to Manager and Approve
        sheet.action_submit_sheet()
        self.assertEquals(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEquals(sheet.state, "approve")
        # Check state != draft, many employee and don't have product
        with self.assertRaises(UserError):
            expense_petty_cash.action_submit_expenses()
        expense_test = expense_petty_cash_2 + expense_petty_cash_3
        with self.assertRaises(UserError):
            expense_test.action_submit_expenses()
        expense_petty_cash_3.product_id = False
        with self.assertRaises(UserError):
            expense_petty_cash_3.action_submit_expenses()
        # Create Expense Entries
        sheet.action_sheet_move_create()
        self.assertEquals(sheet.state, "done")
        self.assertTrue(sheet.account_move_id.id)
        self.assertEquals(self.petty_cash_holder.petty_cash_balance, 600.0)

    def test_03_create_expense_petty_cash_with_journal(self):
        self.petty_cash_holder.journal_id = self.petty_cash_journal_id
        invoice = self._create_invoice(self.partner_1.id)
        with Form(invoice) as inv:
            inv.is_petty_cash = True
            inv.invoice_line_ids.price_unit = 1000.0
        self.assertEqual(invoice.journal_id, self.petty_cash_holder.journal_id)
        invoice.action_post()
        self.petty_cash_holder._compute_petty_cash_balance()
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 1000.0)
        expense_petty_cash = self._create_expense(
            400.0, self.employee_1.id, "petty_cash", self.petty_cash_holder.id
        )
        expense_petty_cash.action_submit_expenses()
        sheet = self._create_expense_sheet(expense_petty_cash)
        self.assertEqual(sheet.journal_id, self.petty_cash_holder.journal_id)
