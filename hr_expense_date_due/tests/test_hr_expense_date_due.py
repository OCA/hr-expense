# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests.common import Form, SavepointCase


class TestHrExpenseDateDue(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.expense_sheet_model = cls.env["hr.expense.sheet"]
        cls.product = cls.env.ref("product.product_product_4")
        cls.pay_terms_a = cls.env.ref("account.account_payment_term_15days")
        cls.payment_term_day = cls.pay_terms_a.line_ids.days
        cls.currency_usd = cls.env.ref("base.USD")
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.main_company = cls.env.ref("base.main_company")
        cls.env.cr.execute(
            """UPDATE res_company SET currency_id = %s
            WHERE id = %s""",
            (cls.main_company.id, cls.currency_usd.id),
        )

        employee_home = cls.env["res.partner"].create(
            {
                "name": "Employee Home Address",
                "property_supplier_payment_term_id": cls.pay_terms_a,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Employee", "address_home_id": employee_home.id}
        )
        cls.expense = cls.create_expense(cls, "Expense")
        cls.expense_currency = cls.create_expense(cls, "Expense", cls.currency_eur.id)

    def create_expense(self, name, currency_id=False):
        """ Returns an open expense """
        expense = self.expense_model.create(
            {
                "name": name,
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "unit_amount": self.product.standard_price,
                "quantity": 1,
                "currency_id": currency_id or self.currency_usd.id,
            }
        )
        expense.action_submit_expenses()
        return expense

    def test_00_config_accounting_date(self):
        """ Test Configuration Accounting Date """
        today = fields.Date.today()
        self.main_company.expense_accounting_current_date = True
        self.assertEqual(self.expense.date, today)
        # Test change expense date is not equal today
        self.expense.date = "2020-01-01"
        self.assertNotEqual(self.expense.date, today)
        expense_sheet = self.expense.sheet_id
        expense_sheet.approve_expense_sheets()
        # Not select accounting date
        self.assertFalse(expense_sheet.accounting_date)
        self.assertFalse(expense_sheet.expense_date_due)
        expense_sheet.action_sheet_move_create()
        self.assertEqual(expense_sheet.state, "post")
        # If not config, accounting date will equal expense date
        self.assertNotEqual(expense_sheet.accounting_date, self.expense.date)
        self.assertEqual(expense_sheet.accounting_date, today)

    def test_01_expense_payment_term(self):
        """ Post Journal Entries with Payment Term """
        today = fields.Date.today()
        expense_sheet = self.expense.sheet_id
        expense_sheet.action_submit_sheet()
        self.assertEqual(expense_sheet.state, "submit")
        expense_sheet.approve_expense_sheets()
        self.assertEqual(expense_sheet.state, "approve")
        self.assertFalse(expense_sheet.accounting_date)
        self.assertTrue(expense_sheet.expense_payment_term_id)
        self.assertEqual(expense_sheet.expense_payment_term_id, self.pay_terms_a)
        self.assertFalse(expense_sheet.expense_date_due)
        # Test due date should be today + payment term
        expense_sheet.action_sheet_move_create()
        self.assertEqual(expense_sheet.state, "post")
        move_line_date = today + relativedelta(days=self.payment_term_day)
        self.assertEqual(expense_sheet.expense_date_due, move_line_date)

    def test_02_expense_payment_term_multi_currency(self):
        """ Post Journal Entries with Payment Term (Multi-Currency)"""
        today = fields.Date.today()
        expense_sheet_currency = self.expense_currency.sheet_id
        expense_sheet_currency.action_submit_sheet()
        self.assertEqual(expense_sheet_currency.state, "submit")
        expense_sheet_currency.approve_expense_sheets()
        self.assertEqual(expense_sheet_currency.state, "approve")
        self.assertFalse(expense_sheet_currency.accounting_date)
        self.assertTrue(expense_sheet_currency.expense_payment_term_id)
        self.assertEqual(
            expense_sheet_currency.expense_payment_term_id, self.pay_terms_a
        )
        self.assertFalse(expense_sheet_currency.expense_date_due)
        # Test due date should be today + payment term
        expense_sheet_currency.action_sheet_move_create()
        self.assertEqual(expense_sheet_currency.state, "post")
        move_line_date = today + relativedelta(days=self.payment_term_day)
        self.assertEqual(expense_sheet_currency.expense_date_due, move_line_date)

    def test_03_expense_no_payment_term(self):
        """ Post Journal Entries without Payment Term """
        expense_sheet = self.expense.sheet_id
        expense_sheet.action_submit_sheet()
        self.assertEqual(expense_sheet.state, "submit")
        expense_sheet.approve_expense_sheets()
        self.assertEqual(expense_sheet.state, "approve")
        self.assertFalse(expense_sheet.accounting_date)
        self.assertTrue(expense_sheet.expense_payment_term_id)
        self.assertEqual(expense_sheet.expense_payment_term_id, self.pay_terms_a)
        # Test onchange accounting date without payment term,
        # expense due date must equal accounting date
        expense_sheet.expense_payment_term_id = False
        with Form(expense_sheet) as sheet:
            sheet.accounting_date = "2021-02-02"
        expense_sheet = sheet.save()
        self.assertFalse(expense_sheet.expense_payment_term_id)
        self.assertEqual(expense_sheet.expense_date_due, expense_sheet.accounting_date)
        self.assertEqual(
            expense_sheet.accounting_date, fields.Date.to_date("2021-02-02")
        )
        expense_sheet.action_sheet_move_create()
        self.assertEqual(expense_sheet.state, "post")
        self.assertEqual(expense_sheet.expense_date_due, expense_sheet.accounting_date)
