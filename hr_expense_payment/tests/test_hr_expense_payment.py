# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon

from ..hooks import post_init_hook


@tagged("-at_install", "post_install")
class TestHrExpensePayment(TestExpenseCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Create expense + sheet + approve
        cls.expense = cls.create_expense(cls)
        res = cls.expense.action_submit_expenses()
        cls.expense_sheet = cls.env[res["res_model"]].browse(res["res_id"])
        cls.expense_sheet.action_approve_expense_sheets()

    def _get_payment_wizard(self):
        res = self.expense_sheet.action_register_payment()
        register_form = Form(self.env[res["res_model"]].with_context(**res["context"]))
        register_form.journal_id = self.company_data["default_journal_bank"]
        register_form.amount = self.expense_sheet.total_amount
        return register_form.save()

    def test_post_init_hook(self):
        self.expense_sheet.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard()
        payment_wizard.action_create_payments()
        payment = self.expense_sheet.payment_ids
        self.assertEqual(len(payment), 1)
        self.assertEqual(len(payment.expense_sheet_ids), 1)
        payment.expense_sheet_ids = False
        # Recompute many2one
        payment = self.expense_sheet.payment_ids
        self.assertFalse(payment)
        self.assertFalse(payment.expense_sheet_ids)
        post_init_hook(self.env)
        self.assertEqual(len(self.expense_sheet.payment_ids), 1)

    def test_get_payment_vals(self):
        self.expense_sheet.action_sheet_move_create()
        payment_wizard = self._get_payment_wizard()
        self.assertFalse(self.expense_sheet.payment_ids)
        payment_wizard.action_create_payments()
        self.assertEqual(len(self.expense_sheet.payment_ids), 1)
