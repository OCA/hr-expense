# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2021 Tecnativa - Pedro M. Baeza
# Copyright 2021-2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("post_install", "-at_install")
class TestHrExpenseInvoice(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].account_sale_tax_id = False
        cls.company_data["company"].account_purchase_tax_id = False
        cls.product_a.supplier_taxes_id = False
        cls.invoice = cls.init_invoice(
            "in_invoice",
            products=[cls.product_a],
        )
        cls.invoice.invoice_line_ids.price_unit = 100
        cls.invoice.invoice_line_ids.tax_ids = False
        cls.invoice.action_post()
        cls.expense = cls.create_expenses(
            {
                "payment_mode": "own_account",
                "product_id": cls.product_a.id,
                "total_amount_currency": 100.0,
                "invoice_id": cls.invoice.id,
            }
        )

    def test_invoice_back_reference(self):
        """account.move.invoice_expense_ids exposes the linked expenses."""
        self.assertIn(self.expense, self.invoice.invoice_expense_ids)

    def test_action_expense_create_invoice(self):
        """action_expense_create_invoice creates a posted bill and links it."""
        expense = self.create_expenses(
            {
                "payment_mode": "own_account",
                "product_id": self.product_a.id,
                "total_amount_currency": 50.0,
            }
        )
        expense.action_expense_create_invoice()
        self.assertTrue(expense.invoice_id)
        self.assertEqual(expense.invoice_id.move_type, "in_invoice")

    def test_amount_mismatch_raises(self):
        """_validate_expense_invoice catches bill-vs-expense amount drift."""
        self.expense.sudo().write({"total_amount_currency": 999.0})
        with self.assertRaises(UserError):
            self.expense._validate_expense_invoice()

    def test_action_post_creates_transfer_entry(self):
        """For own_account bill-linked expenses, action_post creates an AP
        transfer entry instead of a receipt."""
        self.expense.action_submit()
        if self.expense.state == "submitted":
            self.expense.action_approve()
        self.expense.action_post()
        self.assertTrue(self.expense.transfer_move_ids)
        self.assertEqual(self.expense.transfer_move_ids.move_type, "entry")
