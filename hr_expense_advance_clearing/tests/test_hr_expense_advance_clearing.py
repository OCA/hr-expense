# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import Form

from odoo.addons.hr_expense.tests.common import TestExpenseCommon

_logger = logging.getLogger(__name__)


@tagged("post_install", "-at_install")
class TestHrExpenseAdvanceClearing(TestExpenseCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        # Create product type service
        cls.product_d = cls.env["product.product"].create(
            {
                "name": "product_d with type service",
                "property_account_income_id": cls.copy_account(
                    cls.company_data["default_account_revenue"]
                ).id,
                "property_account_expense_id": cls.copy_account(
                    cls.company_data["default_account_expense"]
                ).id,
                "taxes_id": [Command.set((cls.tax_sale_a + cls.tax_sale_b).ids)],
                "supplier_taxes_id": [
                    Command.set((cls.tax_purchase_a + cls.tax_purchase_b).ids)
                ],
                "default_code": "product_d",
                "type": "service",
            }
        )

        tax_group = cls.env["account.tax.group"].create(
            {"name": "Tax Group 1", "sequence": 1}
        )

        cls.tax = cls.env["account.tax"].create(
            {
                "name": "Tax 10.0%",
                "amount": 10.0,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "company_id": cls.company_data["company"].id,
                "tax_group_id": tax_group.id,
                "price_include": True,
            }
        )

        # Get advance product
        cls.product_emp_advance = cls.env.ref(
            "hr_expense_advance_clearing.product_emp_advance"
        )

        # Create advance account with type current asset
        advance_account = cls.env["account.account"].create(
            {
                "code": "154000",
                "name": "Employee Advance",
                "account_type": "asset_current",
                "reconcile": True,
            }
        )

        # Create sale account
        cls.account_sales = cls.env["account.account"].create(
            {
                "code": "X1020",
                "name": "Product Sales - (test)",
                "account_type": "asset_current",
            }
        )

        # Assign advance account to advance product
        cls.product_emp_advance.property_account_expense_id = advance_account

        # Create advance expense 1,000
        cls.advance = cls._create_expense_sheet(
            cls,
            "Advance 1,000",
            cls.expense_employee,
            cls.product_emp_advance,
            1000.0,
            advance=True,
        )

        # Create clearing expense 1,000
        cls.clearing_equal = cls._create_expense_sheet(
            cls, "Buy service 1,000", cls.expense_employee, cls.product_d, 1000.0
        )

        # Create clearing expense 1,200
        cls.clearing_more = cls._create_expense_sheet(
            cls, "Buy service 1,200", cls.expense_employee, cls.product_d, 1200.0
        )

        # Create clearing expense 800
        cls.clearing_less = cls._create_expense_sheet(
            cls, "Buy service 800", cls.expense_employee, cls.product_d, 800.0
        )

    def _create_expense(
        self,
        description,
        employee,
        product,
        amount,
        advance=False,
        payment_mode="own_account",
    ):
        with Form(
            self.env["hr.expense"].with_context(default_advance=advance)
        ) as expense:
            expense.name = description
            expense.employee_id = employee
            if not advance:
                expense.product_id = product
            expense.total_amount_currency = amount
            expense.payment_mode = payment_mode
        expense = expense.save()
        expense.tax_ids = False  # Test no vat
        return expense

    def _create_expense_sheet(
        self, description, employee, product, amount, advance=False
    ):
        expense = self._create_expense(
            self, description, employee, product, amount, advance
        )
        # Add expense to expense sheet
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": description,
                "employee_id": expense.employee_id.id,
                "expense_line_ids": [(6, 0, [expense.id])],
                "advance": advance,
            }
        )
        return expense_sheet

    def _register_payment(self, move_ids, amount, ctx=False, hr_return_advance=False):
        for move_id in move_ids:
            if not ctx:
                ctx = {
                    "active_ids": [move_id.id],
                    "active_id": move_id.id,
                    "active_model": "account.move",
                }
            ctx["hr_return_advance"] = hr_return_advance
            PaymentWizard = self.env["account.payment.register"]
            with Form(PaymentWizard.with_context(**ctx)) as f:
                f.journal_id = self.company_data["default_journal_bank"]
                f.payment_date = fields.Date.today()
                f.amount = amount
            payment_wizard = f.save()
            payment_wizard.action_create_payments()

    def get_new_payment_with_advance(
        self, expense_sheet, amount, ctx=False, hr_return_advance=False
    ):
        """Helper to create payments"""
        if not ctx:
            ctx = {
                "active_model": "account.move",
                "active_ids": expense_sheet.account_move_ids.ids,
            }
        ctx["hr_return_advance"] = hr_return_advance
        with freeze_time(self.frozen_today):
            # if hr_return_advance:
            #     ctx['active_model'] = 'account.move.line'
            payment_register = (
                self.env["account.payment.register"]
                .with_context(**ctx)
                .create(
                    {
                        "amount": amount,
                        "journal_id": self.company_data["default_journal_bank"].id,
                        "payment_method_line_id": self.inbound_payment_method_line.id,
                    }
                )
            )
            if hr_return_advance:
                return payment_register.action_create_payments()
            else:
                return payment_register._create_payments()

    def test_0_test_constraints(self):
        """Test some constraints"""
        # Advance Sheet can't be clearing at the same time.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self.advance.advance_sheet_id = self.advance
        # Advance Sheet can't change account is not the equal
        # Account on Advance Expense's product.
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.product_emp_advance,
                1.0,
                advance=True,
            )
            expense.account_id = self.account_sales.id
            expense._check_advance()
        # Advance Sheet should not have > 1 expense lines
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Buy service 1,000", self.expense_employee, self.product_d, 1.0
            )
            self.advance.write({"expense_line_ids": [(4, expense.id)]})
        # Advance Expense's product, must not has tax involved
        with self.assertRaises(ValidationError):
            self.product_emp_advance.supplier_taxes_id |= self.tax
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.product_emp_advance,
                1.0,
                advance=True,
            )
        self.product_emp_advance.supplier_taxes_id = False  # Remove tax bf proceed
        # Advance Expense, must not paid by company
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.product_emp_advance,
                1.0,
                advance=True,
                payment_mode="company_account",
            )
        # Advance Expense, must be product advance only
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.product_emp_advance,
                1.0,
                advance=True,
            )
            expense.product_id = self.product_d.id
            expense._check_advance()
        # Advance Expense's product must have account configured
        with self.assertRaises(ValidationError):
            self.product_emp_advance.property_account_expense_id = False
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.product_emp_advance,
                1.0,
                advance=True,
            )

    def test_1_clear_equal_advance(self):
        """When clear equal advance, all set"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_create()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self.get_new_payment_with_advance(self.advance, 1000.0)
        self.assertRecordValues(
            self.advance, [{"payment_state": "paid", "state": "done"}]
        )
        self.assertEqual(self.advance.state, "done")
        # ------------------ Clearing --------------------------
        # Clear this with previous advance
        vals = self.advance.open_clear_advance()  # Test Clear Advance button
        ctx = vals.get("context")
        self.assertEqual(ctx["default_advance_sheet_id"], self.advance.id)
        self.clearing_equal.advance_sheet_id = self.advance
        self.assertEqual(self.clearing_equal.advance_sheet_residual, 1000.0)
        self.clearing_equal.action_submit_sheet()
        self.clearing_equal.action_approve_expense_sheets()
        self.clearing_equal.action_sheet_move_create()
        # Equal amount, state change to Paid and advance is cleared
        self.assertRecordValues(
            self.clearing_equal, [{"payment_state": "paid", "state": "done"}]
        )
        self.assertEqual(self.clearing_equal.advance_sheet_residual, 0.0)
        # Clear this with previous advance is done
        self.clearing_more.advance_sheet_id = self.advance
        self.clearing_more.action_submit_sheet()
        self.clearing_more.action_approve_expense_sheets()
        with self.assertRaises(ValidationError):
            self.clearing_more.action_sheet_move_create()
        # There are 2 clearing in advance
        self.assertEqual(self.advance.clearing_count, 2)
        # Check link clearing in advance must be equal clearing count
        clearing_dict = self.advance.action_open_clearings()
        self.assertEqual(
            len(clearing_dict["domain"][0][2]), self.advance.clearing_count
        )
        # Check advance from employee
        self.assertEqual(self.expense_employee.advance_count, 1)
        clearing_document = self.expense_employee.action_open_advance_clearing()
        self.assertEqual(
            len(clearing_document["domain"][0][2]), self.expense_employee.advance_count
        )
        # Check back state move in advance after create clearing
        with self.assertRaises(UserError):
            self.advance.account_move_ids.button_draft()
        with self.assertRaises(UserError):
            self.advance.account_move_ids.button_cancel()
        with self.assertRaises(UserError):
            self.advance.account_move_ids._reverse_moves()

    def test_2_clear_more_than_advance(self):
        """When clear more than advance, do pay more"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_create()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self.get_new_payment_with_advance(self.advance, 1000.0)
        self.assertRecordValues(
            self.advance, [{"payment_state": "paid", "state": "done"}]
        )
        # ------------------ Clearing --------------------------
        # Clear this with previous advance
        self.clearing_more.advance_sheet_id = self.advance
        self.assertEqual(self.clearing_more.advance_sheet_residual, 1000.0)
        self.clearing_more.action_submit_sheet()
        self.clearing_more.action_approve_expense_sheets()
        self.clearing_more.action_sheet_move_create()
        # More amount, state not changed to paid, and has to pay 200 more
        self.assertRecordValues(self.clearing_more, [{"state": "post"}])
        self.assertEqual(self.clearing_more.amount_payable, 200.0)
        self.get_new_payment_with_advance(self.clearing_more, 200.0)
        self.assertRecordValues(self.clearing_more, [{"state": "done"}])

    def test_3_clear_less_than_advance(self):
        """When clear less than advance, do return advance"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_create()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        # Test return advance register payment with move state draft
        with self.assertRaises(UserError):
            self.advance.account_move_ids.button_draft()
            self.get_new_payment_with_advance(
                self.advance, 200.0, hr_return_advance=True
            )
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self.get_new_payment_with_advance(self.advance, 1000.0)
        self.assertRecordValues(self.advance, [{"state": "done"}])
        # ------------------ Clearing, Return Advance --------------------------
        # Clear this with previous advance
        self.clearing_less.advance_sheet_id = self.advance
        self.assertEqual(self.clearing_less.advance_sheet_residual, 1000.0)
        self.clearing_less.action_submit_sheet()
        self.clearing_less.action_approve_expense_sheets()
        register_payment = self.advance.with_context(
            hr_return_advance=True
        ).action_register_payment()
        # Test return advance register payment without move
        with self.assertRaises(UserError):
            self.get_new_payment_with_advance(
                self.env["hr.expense.sheet"], 200.0, hr_return_advance=True
            )
        # Test return advance over residual
        with self.assertRaises(UserError):
            self.get_new_payment_with_advance(
                self.advance, 300.0, register_payment["context"], hr_return_advance=True
            )
        self.clearing_less.action_sheet_move_create()
        # Less amount, state set to done. Still remain 200 to be returned
        self.assertEqual(self.clearing_less.state, "done")
        self.assertEqual(self.clearing_less.advance_sheet_residual, 200.0)
        # Back to advance and do return advance, clearing residual become 0.0
        self._register_payment(
            self.advance.account_move_ids,
            200.0,
            ctx=register_payment["context"],
            hr_return_advance=True,
        )
        self.assertEqual(self.advance.clearing_residual, 0.0)
        # Check payment of return advance
        payment = self.env["account.payment"].search(
            [("advance_id", "=", self.advance.id)]
        )
        self.assertEqual(len(payment), 1)

    def test_4_clearing_product_advance(self):
        """When select clearing product on advance"""
        # ------------------ Advance --------------------------
        self.advance.expense_line_ids.clearing_product_id = self.product_d
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_create()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_ids, 1000.0)
        self.assertEqual(self.advance.state, "done")
        # ------------------ Clearing --------------------------
        with Form(self.env["hr.expense.sheet"]) as sheet:
            sheet.name = "Test Clearing"
            sheet.employee_id = self.expense_employee
        ex_sheet = sheet.save()
        ex_sheet.advance_sheet_id = self.advance
        self.assertEqual(len(ex_sheet.expense_line_ids), 0)
        ex_sheet._onchange_advance_sheet_id()
        self.assertEqual(len(ex_sheet.expense_line_ids), 1)
        reverse_move = self.advance.account_move_ids._reverse_moves(
            default_values_list=[
                {"invoice_date": self.advance.account_move_ids.date, "ref": False}
            ],
            cancel=True,
        )
        self.assertNotEqual(reverse_move, self.advance.account_move_ids)
