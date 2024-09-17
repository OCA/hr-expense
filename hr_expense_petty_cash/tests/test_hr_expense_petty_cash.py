# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import Form, TransactionCase


class TestHrExpensePettyCash(TransactionCase):
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

    def _create_expense(self, amount, employee_id, mode, petty_cash_holder=False):
        expense = self.exp_obj.create(
            {
                "name": "Expense - Test",
                "employee_id": employee_id,
                "product_id": self.product.id,
                "unit_amount": amount,
                "payment_mode": mode,
                "petty_cash_id": petty_cash_holder,
            }
        )
        return expense

    def _create_expense_sheet(self, expenses):
        expense_sheet = self.sheet_obj.create(
            {
                "name": expenses[0].name,
                "employee_id": expenses[0].employee_id.id,
                "expense_line_ids": [(6, 0, expenses.ids)],
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
            sheet.expense_line_ids.unit_amount = 1600.0
            sheet._check_petty_cash_amount()
        sheet.expense_line_ids.unit_amount = 400.0
        # Submitted to Manager and Approve
        sheet.action_submit_sheet()
        self.assertEqual(sheet.state, "submit")
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
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
        self.assertEqual(sheet.state, "done")
        self.assertTrue(sheet.account_move_id.id)
        self.assertEqual(self.petty_cash_holder.petty_cash_balance, 600.0)

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
