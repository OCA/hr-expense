# Copyright 2021 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from ast import literal_eval

from odoo import fields
from odoo.exceptions import UserError

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestReInvoiceManual(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_expense_auto = cls.env["product.product"].create(
            {
                "name": "Expense Auto (default)",
                "lst_price": 1000.0,
                "expense_policy": "sales_price",
                "expense_mode": "auto",
            }
        )
        cls.product_expense_manual = cls.env["product.product"].create(
            {
                "name": "Expense Manual",
                "lst_price": 1000.0,
                "expense_policy": "sales_price",
                "expense_mode": "manual",
            }
        )
        cls.order = cls.env["sale.order"].create({"partner_id": cls.partner_a.id})
        cls.order._create_analytic_account()
        cls.order.action_confirm()
        cls.expense_sheet = cls.env["hr.expense.sheet"].create(
            {
                "name": "Expense Sheet",
                "employee_id": cls.expense_employee.id,
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "accounting_date": fields.Date.today(),
            }
        )
        cls.expense = cls.env["hr.expense"].create(
            {
                "sheet_id": cls.expense_sheet.id,
                "employee_id": cls.expense_employee.id,
                "name": "Expense",
                "date": fields.Date.today(),
                "product_id": cls.product_expense_manual.id,
                "unit_amount": cls.product_expense_manual.lst_price,
                "sale_order_id": cls.order.id,
            }
        )

    def _get_expenses_to_reinvoice(self, with_discarded=False):
        """Gets the expenses to reinvoice from the UI menu action"""
        xml_id = "sale_expense_manual_reinvoice.action_hr_expense_to_reinvoice"
        action = self.env["ir.actions.act_window"]._for_xml_id(xml_id)
        domain = literal_eval(action["domain"].strip())
        if not with_discarded:
            domain += [("manual_reinvoice_discarded", "=", False)]
        return self.env["hr.expense"].search(domain)

    def test_expense_manual_reinvoice(self):
        """Test the full manual reinvoice flow"""
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        self.assertTrue(self.expense.manual_reinvoice)
        self.assertFalse(self.order.order_line, "No expense should've been created yet")
        # Check the re-invoice menu
        self.assertIn(
            self._get_expenses_to_reinvoice(),
            self.expense,
            "The expense should've been found in the to re-invoice menu",
        )
        # Check that we can re-invoice the expense
        self.expense.action_manual_reinvoice()
        self.assertTrue(self.expense.manual_reinvoice_done)
        self.assertTrue(self.order.order_line, "The expense should've been reinvoiced")
        # Check that we can't re-invoice it again
        with self.assertRaisesRegex(UserError, "Expense already re-invoiced"):
            self.expense.action_manual_reinvoice()

    def test_expense_manual_reinvoice_without_sale_order(self):
        """Test case without sale order on hr.expense"""
        self.expense.sale_order_id = False
        self.expense.analytic_account_id = self.order.analytic_account_id
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        self.assertFalse(self.order.order_line, "No expense should've been created yet")
        # Check the re-invoice menu
        self.assertIn(
            self._get_expenses_to_reinvoice(),
            self.expense,
            "The expense should've been found in the to re-invoice menu",
        )
        # Check that we can't re-invoice without the user filling the targeted order id
        error_message = (
            "Some expenses are missing the Customer to Reinvoice, "
            "please fill this field on all lines and try again."
        )
        with self.assertRaisesRegex(UserError, error_message):
            self.expense.action_manual_reinvoice()
        # Check that we can re-invoice the expense if we fill the sale order
        self.expense.sale_order_id = self.order
        self.expense.action_manual_reinvoice()
        self.assertTrue(self.expense.manual_reinvoice_done)
        self.assertTrue(self.order.order_line, "The expense should've been reinvoiced")

    def test_expense_auto_reinvoice(self):
        """Test that the normal flow still works"""
        self.expense.product_id = self.product_expense_auto
        self.expense.unit_amount = 1500.0  # amount resets after product change
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        self.assertFalse(self.expense.manual_reinvoice)
        self.assertTrue(self.order.order_line, "The expense should've been reinvoiced")
        # Check the re-invoice menu
        self.assertNotIn(
            self._get_expenses_to_reinvoice(),
            self.expense,
            "The expense shouldn't have been found in the to re-invoice menu",
        )
        # Check that we can't re-invoice this expense
        with self.assertRaisesRegex(
            UserError,
            "Only manually re-invoice expenses can be re-invoiced",
        ):
            self.expense.action_manual_reinvoice()

    def test_expense_manual_reinvoice_discard(self):
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        # Check the re-invoice menu
        self.assertIn(
            self._get_expenses_to_reinvoice(),
            self.expense,
            "The expense should've been found in the to re-invoice menu",
        )
        self.expense.action_manual_reinvoice_discard()
        self.assertTrue(self.expense.manual_reinvoice_discarded)
        # Check the re-invoice menu
        self.assertNotIn(
            self._get_expenses_to_reinvoice(),
            self.expense,
            "The expense shouldn't have been found in the to re-invoice menu",
        )
        # We should still be able to find it removing the "to reinvoice" filter
        self.assertIn(
            self._get_expenses_to_reinvoice(with_discarded=True),
            self.expense,
            "The expense should've been found in the to re-invoice menu",
        )
        # We should be able to re-invoice it, even if it was discarded
        self.expense.action_manual_reinvoice()
        self.assertTrue(self.expense.manual_reinvoice_done)
        self.assertFalse(self.expense.manual_reinvoice_discarded, "Back to false")
        self.assertTrue(self.order.order_line, "The expense should've been reinvoiced")
