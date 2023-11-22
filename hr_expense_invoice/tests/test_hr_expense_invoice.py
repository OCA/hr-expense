# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2021 Tecnativa - Pedro M. Baeza
# Copyright 2021-2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT
from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("post_install", "-at_install")
class TestHrExpenseInvoice(TestExpenseCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.account_payment_register = cls.env["account.payment.register"]
        cls.payment_obj = cls.env["account.payment"]
        cls.cash_journal = cls.company_data["default_journal_cash"]
        cls.company_data["company"].account_sale_tax_id = False
        cls.company_data["company"].account_purchase_tax_id = False
        cls.product_a.supplier_taxes_id = False
        cls.invoice = cls.init_invoice(
            "in_invoice",
            products=[cls.product_a],
        )
        cls.invoice.invoice_line_ids.price_unit = 100
        cls.invoice2 = cls.invoice.copy(
            {
                "invoice_date": fields.Date.today(),
            }
        )
        cls.expense_employee.address_home_id.write(
            {
                "bank_ids": [
                    (
                        0,
                        0,
                        {
                            "acc_number": "FR20 1242 1242 1242 1242 1242 124",
                        },
                    )
                ],
            }
        )
        cls.expense_employee.bank_account_id = (
            cls.expense_employee.address_home_id.bank_ids
        )
        cls.expense = cls.env["hr.expense"].create(
            {
                "name": "Expense test",
                "employee_id": cls.expense_employee.id,
                "product_id": cls.product_a.id,
                "unit_amount": 50.00,
            }
        )
        cls._create_attachment(cls, cls.expense._name, cls.expense.id)
        cls.expense2 = cls.expense.copy()
        cls._create_attachment(cls, cls.expense2._name, cls.expense2.id)
        cls.expense3 = cls.expense.copy()
        cls._create_attachment(cls, cls.expense3._name, cls.expense3.id)

    def _invoice_register_payment(self, invoice):
        res = invoice.action_register_payment()
        payment_form = Form(self.env[res["res_model"]].with_context(**res["context"]))
        payment_form.journal_id = self.cash_journal
        return payment_form.save()

    def _register_payment(self, sheet):
        res = sheet.action_register_payment()
        register_payment_form = Form(
            self.env[res["res_model"]].with_context(**res["context"])
        )
        register_payment_form.journal_id = self.cash_journal
        register = register_payment_form.save()
        res2 = register.action_create_payments()
        payment = self.env[res2["res_model"]].browse(res2["res_id"])
        self.assertEqual(len(payment), 1)
        self.assertEqual(sheet.payment_state, "paid")

    def _create_attachment(self, res_model, res_id):
        return self.env["ir.attachment"].create(
            {
                "name": "Test attachment %s (%s)" % (res_id, res_model),
                "res_model": res_model,
                "res_id": res_id,
                "datas": base64.b64encode(b"\xff data"),
            }
        )

    def _action_submit_expenses(self, expenses):
        res = expenses.action_submit_expenses()
        sheet_form = Form(self.env[res["res_model"]].with_context(**res["context"]))
        return sheet_form.save()

    def test_0_hr_tests_misc(self):
        self.assertEqual(self.expense.attachment_number, 1)
        self.assertEqual(self.expense2.attachment_number, 1)
        self.assertEqual(self.expense3.attachment_number, 1)

    def test_0_hr_test_no_invoice(self):
        # We add an expense
        sheet = self._action_submit_expenses(self.expense)
        self.assertIn(self.expense, sheet.expense_line_ids)
        self.assertAlmostEqual(self.expense.total_amount, 50.0)
        # We approve sheet, no invoice
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        self.assertFalse(sheet.account_move_id)
        # We post journal entries
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertTrue(sheet.account_move_id)
        # We make payment on expense sheet
        self._register_payment(sheet)

    def test_1_hr_test_invoice(self):
        # We add an expense
        self.expense.unit_amount = 100
        sheet = self._action_submit_expenses(self.expense)
        self.assertIn(self.expense, sheet.expense_line_ids)
        # We add invoice to expense
        self.invoice.action_post()  # residual = 100
        with Form(self.expense) as f:
            f.invoice_id = self.invoice
        # Test that invoice can't register payment by itself
        payment = self._invoice_register_payment(self.invoice)
        with self.assertRaises(ValidationError):
            payment.action_create_payments()
        # We approve sheet
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        self.assertFalse(sheet.account_move_id)
        self.assertEqual(self.invoice.state, "posted")
        # Test state not posted
        self.invoice.button_draft()
        self.assertEqual(self.invoice.state, "draft")
        with self.assertRaises(UserError):
            sheet.action_sheet_move_create()
        self.invoice.action_post()
        self.assertEqual(self.invoice.state, "posted")
        # We post journal entries
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertEqual(sheet.payment_state, "partial")
        self.assertTrue(sheet.account_move_id)
        # Invoice is now paid
        self.assertEqual(self.invoice.payment_state, "paid")
        # We make payment on expense sheet
        self._register_payment(sheet)

    def test_1_hr_test_invoice_paid_by_company(self):
        # We add an expense
        self.expense.unit_amount = 100
        self.expense.payment_mode = "company_account"
        sheet = self._action_submit_expenses(self.expense)
        self.assertIn(self.expense, sheet.expense_line_ids)
        # We add invoice to expense
        self.invoice.action_post()  # residual = 100.0
        self.expense.invoice_id = self.invoice
        # Test that invoice can't register payment by itself
        payment = self._invoice_register_payment(self.invoice)
        with self.assertRaises(ValidationError):
            payment.action_create_payments()
        # We approve sheet
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        self.assertFalse(sheet.account_move_id)
        self.assertEqual(self.invoice.state, "posted")
        # We post journal entries
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "done")
        self.assertTrue(sheet.account_move_id)
        # Invoice is not paid
        self.assertEqual(self.invoice.payment_state, "not_paid")
        # Click on View Invoice button link to the correct invoice
        res = sheet.action_view_invoices()
        self.assertEqual(res["view_mode"], "form")

    def test_2_hr_test_multi_invoices(self):
        # We add 2 expenses
        self.expense.unit_amount = 100
        self.expense2.unit_amount = 100
        expenses = self.expense + self.expense2
        sheet = self._action_submit_expenses(expenses)
        self.assertIn(self.expense, sheet.expense_line_ids)
        self.assertIn(self.expense2, sheet.expense_line_ids)
        # We add invoices to expenses
        self.invoice.action_post()
        self.invoice2.action_post()
        self.expense.invoice_id = self.invoice.id
        self.expense2.invoice_id = self.invoice2.id
        self.assertAlmostEqual(self.expense.total_amount, 100)
        self.assertAlmostEqual(self.expense2.total_amount, 100)
        # We approve sheet
        sheet.approve_expense_sheets()
        self.assertEqual(sheet.state, "approve")
        self.assertFalse(sheet.account_move_id)
        self.assertEqual(self.invoice.state, "posted")
        # We post journal entries
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertTrue(sheet.account_move_id)
        # Invoice is now paid
        self.assertEqual(self.invoice.payment_state, "paid")
        self.assertEqual(self.invoice2.payment_state, "paid")
        # We make payment on expense sheet
        self._register_payment(sheet)

    def test_3_hr_test_expense_create_invoice(self):
        # We add 2 expenses
        expenses = self.expense + self.expense2
        sheet = self._action_submit_expenses(expenses)
        self.assertIn(self.expense, sheet.expense_line_ids)
        self.assertIn(self.expense2, sheet.expense_line_ids)
        self.expense.action_expense_create_invoice()
        self.assertTrue(self.expense.invoice_id)
        self.assertAlmostEqual(self.expense.invoice_id.message_attachment_count, 1)
        self.assertEqual(sheet.invoice_count, 1)
        sheet.invalidate_recordset()
        self.expense2.action_expense_create_invoice()
        self.assertTrue(self.expense2.invoice_id)
        self.assertAlmostEqual(self.expense2.invoice_id.message_attachment_count, 1)
        self.assertEqual(sheet.invoice_count, 2)
        # Only change invoice not assigned to expense yet
        with self.assertRaises(ValidationError):
            self.expense.invoice_id.amount_total = 60
        # Force to change
        invoice = self.expense2.invoice_id
        self.expense2.invoice_id = False
        invoice.amount_total = 50
        self.assertEqual(self.expense2.total_amount, 50)
        # Set invoice_id again to expense2
        self.expense2.invoice_id = invoice
        # Validate invoices
        self.expense.invoice_id.partner_id = self.partner_a
        self.expense.invoice_id.action_post()
        self.expense2.invoice_id.partner_id = self.partner_a
        self.expense2.invoice_id.action_post()
        # We approve sheet
        sheet.approve_expense_sheets()
        # We post journal entries
        sheet.action_sheet_move_create()
        self.assertEqual(sheet.state, "post")
        self.assertTrue(sheet.account_move_id)
        # Invoice are now paid
        self.assertEqual(self.expense.invoice_id.state, "posted")
        self.assertEqual(self.expense.invoice_id.payment_state, "paid")
        self.assertEqual(self.expense2.invoice_id.state, "posted")
        self.assertEqual(self.expense2.invoice_id.payment_state, "paid")
        # We make payment on expense sheet
        self._register_payment(sheet)
        # Click on View Invoice button link to the correct invoice
        res = sheet.action_view_invoices()
        self.assertEqual(res["view_mode"], "tree,form")

    def test_4_hr_expense_constraint(self):
        # Only invoice with status open is allowed
        with self.assertRaises(UserError):
            self.expense.write({"invoice_id": self.invoice.id})
        # We add an expense, total_amount now = 50.0
        sheet = self._action_submit_expenses(self.expense)
        # We add invoice to expense
        self.invoice.amount_total = 100
        self.invoice.action_post()  # residual = 100.0
        self.expense.invoice_id = self.invoice
        # Amount must equal, expense vs invoice
        with self.assertRaises(UserError):
            sheet._validate_expense_invoice()
        self.expense.write({"unit_amount": 100.0})  # set to 100.0
        sheet._validate_expense_invoice()

    def test_5_hr_test_multi_invoice(self):
        # We add 2 expenses
        self.expense.unit_amount = 200.0
        self.expense2.unit_amount = 100.0
        expenses = self.expense + self.expense2
        sheet = self._action_submit_expenses(expenses)
        self.assertIn(self.expense, sheet.expense_line_ids)
        self.assertIn(self.expense2, sheet.expense_line_ids)
        # We add invoice to expense
        self.expense2.action_expense_create_invoice()
        self.assertAlmostEqual(self.expense2.invoice_id.message_attachment_count, 1)
        self.expense2.invoice_id.partner_id = self.partner_a
        self.expense2.invoice_id.action_post()
        # We approve sheet
        sheet.approve_expense_sheets()
        # We post journal entries
        sheet.action_sheet_move_create()
        self.assertEqual(self.expense2.invoice_id.payment_state, "paid")
        line_expense_2 = sheet.account_move_id.line_ids.filtered(
            lambda x: x.debit == 100
        )
        self.assertEqual(line_expense_2.partner_id, self.invoice.partner_id)
        line_expense_1 = sheet.account_move_id.line_ids.filtered(
            lambda x: x.debit == 200
        )
        self.assertNotEqual(line_expense_2.account_id, line_expense_1.account_id)
        self.assertEqual(sheet.state, "post")
