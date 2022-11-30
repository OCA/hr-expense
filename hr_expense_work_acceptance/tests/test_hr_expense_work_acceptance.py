# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import ast

from odoo.exceptions import UserError
from odoo.tests.common import Form, TransactionCase


class TestHrExpensePayToVendor(TransactionCase):
    def setUp(self):
        super(TestHrExpensePayToVendor, self).setUp()
        self.vendor = self.env["res.partner"].create({"name": "Test Vendor"})
        self.payment_obj = self.env["account.payment"]
        self.account_payment_register = self.env["account.payment.register"]
        self.payment_journal = self.env["account.journal"].search(
            [("type", "in", ["cash", "bank"])], limit=1
        )

        self.main_company = company = self.env.ref("base.main_company")
        # Enable and Config WA
        self.env["res.config.settings"].create(
            {"group_wa_accepted_before_inv": True, "group_enable_wa_on_exp": True}
        ).execute()

        self.expense_journal = self.env["account.journal"].create(
            {
                "name": "Purchase Journal - Test",
                "code": "HRTPJ",
                "type": "purchase",
                "company_id": company.id,
            }
        )
        self.expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "employee_id": self.ref("hr.employee_admin"),
                "name": "Expense test",
                "journal_id": self.expense_journal.id,
            }
        )
        self.expenses = self.env["hr.expense"].create(
            [
                {
                    "name": "Expense Line 1",
                    "employee_id": self.ref("hr.employee_admin"),
                    "product_id": self.ref("hr_expense.air_ticket"),
                    "unit_amount": 1,
                    "quantity": 10,
                    "sheet_id": self.expense_sheet.id,
                },
                {
                    "name": "Expense Line 1",
                    "employee_id": self.ref("hr.employee_admin"),
                    "product_id": self.ref("hr_expense.air_ticket"),
                    "unit_amount": 1,
                    "quantity": 20,
                    "sheet_id": self.expense_sheet.id,
                },
            ]
        )

    def test_01_hr_expense_work_acceptance(self):
        """When expense is set to pay to vendor, I expect,
        - After post journal entries, all journal items will use partner_id = vendor
        - After make payment, all journal items will use partner_id = vendor
        """
        # No WA
        self.assertEqual(len(self.expense_sheet.wa_ids), 0)
        self.assertEqual(self.expense_sheet.wa_count, 0)
        self.assertEqual(self.expense_sheet.wa_accepted, 0)
        for expense in self.expenses:
            self.assertEqual(expense.qty_accepted, 0)
        # Create 2 WA
        res = self.expense_sheet.with_context(create_wa=True).action_view_wa()
        f = Form(self.env[res["res_model"]].with_context(res["context"]))
        wa_ids = work_acceptance = f.save()
        self.assertEqual(work_acceptance.state, "draft")
        work_acceptance.button_cancel()
        self.assertEqual(work_acceptance.state, "cancel")
        res = self.expense_sheet.with_context(create_wa=True).action_view_wa()
        f = Form(self.env[res["res_model"]].with_context(res["context"]))
        work_acceptance = f.save()
        wa_ids += work_acceptance
        # Check smart button link to 2 WA
        self.assertEqual(len(self.expense_sheet.wa_ids), 2)
        res = self.expense_sheet.with_context().action_view_wa()
        domain = ast.literal_eval(res.get("domain", False))
        self.assertEqual(domain[0][2], wa_ids.ids)
        self.assertEqual(self.expense_sheet.wa_count, 2)
        self.assertEqual(self.expense_sheet.wa_accepted, 0)  # wa not accept
        # WA Accepted
        work_acceptance.button_accept()
        for expense in self.expenses:
            self.assertEqual(expense.qty_accepted, expense.quantity)
        self.assertEqual(len(self.expense_sheet.wa_ids), 2)
        self.assertEqual(self.expense_sheet.wa_count, 2)
        # recompute, expense sheet should accepted wa
        self.expense_sheet._compute_wa_accepted()
        self.assertEqual(self.expense_sheet.wa_accepted, 1)

    def test_02_hr_expense_required_wa(self):
        """Test Config WA"""
        self.expense_sheet.action_submit_sheet()
        self.expense_sheet.approve_expense_sheets()
        # Test post journal entry without WA
        with self.assertRaises(UserError):
            self.expense_sheet.action_sheet_move_create()
        # Test create wa but not accepted
        res = self.expense_sheet.with_context(create_wa=True).action_view_wa()
        f = Form(self.env[res["res_model"]].with_context(res["context"]))
        work_acceptance = f.save()
        res = self.expense_sheet.with_context().action_view_wa()
        self.assertEqual(res["res_id"], self.expense_sheet.wa_ids.id)
        with self.assertRaises(UserError):
            self.expense_sheet.action_sheet_move_create()
        work_acceptance.button_accept()
        self.expense_sheet.action_sheet_move_create()
