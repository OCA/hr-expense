# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged
from odoo.tools import mute_logger

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpenseAdvanceClearing(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        advance_account = cls.company_data["default_account_deferred_expense"]
        advance_account.reconcile = True
        cls.emp_advance = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        cls.emp_advance.property_account_expense_id = advance_account
        cls.product_a.standard_price = 0
        # Create advance expense 1,000
        cls.advance = cls._create_expense_sheet(
            cls,
            "Advance 1,000",
            cls.expense_employee,
            cls.emp_advance,
            1000.0,
            advance=True,
        )
        # Create clearing expense 1,000
        cls.clearing_equal = cls._create_expense_sheet(
            cls, "Buy service 1,000", cls.expense_employee, cls.product_a, 1000.0
        )
        # Create clearing expense 1,200
        cls.clearing_more = cls._create_expense_sheet(
            cls, "Buy service 1,200", cls.expense_employee, cls.product_a, 1200.0
        )
        # Create clearing expense 800
        cls.clearing_less = cls._create_expense_sheet(
            cls, "Buy service 800", cls.expense_employee, cls.product_a, 800.0
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

    def _register_payment(self, move_id, amount, ctx=False, hr_return_advance=False):
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

    def test_0_test_constraints(self):
        """Test some constraints"""
        # Advance Sheet can't be clearing at the same time.
        with self.assertRaises(ValidationError):
            self.advance.advance_sheet_id = self.advance
        # Advance Sheet can't change account is not the equal
        # Account on Advance Expense's product.
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.emp_advance,
                1.0,
                advance=True,
            )
            expense.account_id = self.company_data["default_account_payable"]
            expense._check_advance()
        # Advance Sheet should not have > 1 expense lines
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Buy service 1,000", self.expense_employee, self.product_a, 1.0
            )
            self.advance.write({"expense_line_ids": [(4, expense.id)]})
        # Advance Expense's product, must not has tax involved
        with self.assertRaises(ValidationError):
            self.emp_advance.supplier_taxes_id |= self.company_data[
                "default_tax_purchase"
            ]
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.emp_advance,
                1.0,
                advance=True,
            )
        self.emp_advance.supplier_taxes_id = False  # Remove tax bf proceed
        # Advance Expense, must not paid by company
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.emp_advance,
                1.0,
                advance=True,
                payment_mode="company_account",
            )
        # Advance Expense, must be product advance only
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.emp_advance,
                1.0,
                advance=True,
            )
            expense.product_id = self.product_a
            expense._check_advance()
        # Advance Expense's product must have account configured
        with self.assertRaises(ValidationError):
            self.emp_advance.property_account_expense_id = False
            expense = self._create_expense(
                "Advance 1,000",
                self.expense_employee,
                self.emp_advance,
                1.0,
                advance=True,
            )

    @mute_logger("odoo.models.unlink")
    def test_1_clear_equal_advance(self):
        """When clear equal advance, all set"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_post()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_ids, 1000.0)
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
        self.clearing_equal.action_sheet_move_post()
        # Equal amount, state change to Paid and advance is cleared
        self.assertEqual(self.clearing_equal.state, "done")
        self.assertEqual(self.clearing_equal.advance_sheet_residual, 0.0)
        # Clear this with previous advance is done
        self.clearing_more.advance_sheet_id = self.advance
        self.clearing_more.action_submit_sheet()
        # Can't approved clearing, because advance residual is 0.0
        with self.assertRaises(ValidationError):
            self.clearing_more.action_approve_expense_sheets()
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

    @mute_logger("odoo.models.unlink")
    def test_2_clear_more_than_advance(self):
        """When clear more than advance, do pay more"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_post()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_ids, 1000.0)
        self.assertEqual(self.advance.state, "done")
        # ------------------ Clearing --------------------------
        # Clear this with previous advance
        self.clearing_more.advance_sheet_id = self.advance
        self.assertEqual(self.clearing_more.advance_sheet_residual, 1000.0)
        self.clearing_more.action_submit_sheet()
        self.clearing_more.action_approve_expense_sheets()
        self.clearing_more.action_sheet_move_post()
        # More amount, state not changed to paid, and has to pay 200 more
        self.assertEqual(self.clearing_more.state, "post")
        self.assertEqual(self.clearing_more.amount_payable, 200.0)
        self._register_payment(self.clearing_more.account_move_ids, 200.0)
        self.assertEqual(self.clearing_more.state, "done")

    @mute_logger("odoo.models.unlink")
    def test_3_clear_less_than_advance(self):
        """When clear less than advance, do return advance"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_post()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_ids, 1000.0)
        self.assertEqual(self.advance.state, "done")
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
            self._register_payment(
                self.env["account.move"], 200.0, hr_return_advance=True
            )
        # Test return advance over residual
        with self.assertRaises(UserError):
            self._register_payment(
                self.advance.account_move_ids,
                300.0,
                ctx=register_payment["context"],
                hr_return_advance=True,
            )
        self.clearing_less.action_sheet_move_post()
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

    @mute_logger("odoo.models.unlink")
    def test_4_clearing_product_advance(self):
        """When select clearing product on advance"""
        # ------------------ Advance --------------------------
        self.advance.expense_line_ids.clearing_product_id = self.product_a
        self.advance.action_submit_sheet()
        self.advance.action_approve_expense_sheets()
        self.advance.action_sheet_move_post()
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
