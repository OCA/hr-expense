# Copyright 2026 - TODAY, Wesley Oliveira <wesley.oliveira@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpensePaymentTerm(TestExpenseCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.payment_term = cls.env.ref("account.account_payment_term_30days")

        expense_form = Form(
            cls.env["hr.expense"].with_context(
                default_product_id=cls.product_a.id,
                default_employee_id=cls.expense_employee.id,
            )
        )
        expense_form.name = "Expense with payment term"
        cls.expense = expense_form.save()
        res = cls.expense.action_submit_expenses()
        sheet_form = Form(cls.env[res["res_model"]].with_context(**res["context"]))
        cls.expense_sheet_1 = sheet_form.save()
        cls.expense_sheet_1.payment_term_id = cls.payment_term
        cls.expense_sheet_1.approve_expense_sheets()

        expense_form_2 = Form(
            cls.env["hr.expense"].with_context(
                default_product_id=cls.product_a.id,
                default_employee_id=cls.expense_employee.id,
            )
        )
        expense_form_2.name = "Expense with date due"
        cls.expense_2 = expense_form_2.save()
        res = cls.expense_2.action_submit_expenses()
        sheet_form = Form(cls.env[res["res_model"]].with_context(**res["context"]))
        cls.expense_sheet_2 = sheet_form.save()
        cls.expense_sheet_2.invoice_date_due = fields.Date.today()
        cls.expense_sheet_2._do_approve()

    def test_payment_term_is_propagated_to_expense_move(self):
        self.expense_sheet_1.action_sheet_move_create()
        self.assertEqual(
            self.expense_sheet_1.account_move_id.invoice_payment_term_id,
            self.payment_term,
        )

    def test_invoice_date_due_is_propagated_to_expense_move(self):
        self.expense_sheet_2.action_sheet_move_create()
        self.assertFalse(self.expense_sheet_2.account_move_id.invoice_payment_term_id)
        self.assertEqual(
            self.expense_sheet_2.account_move_id.invoice_date_due,
            fields.Date.today(),
        )
