# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import common
from odoo.tests.common import Form


class TestHrExpenseAdvanceClearing(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref("base.main_company")
        cls.company_2 = cls.env["res.company"].create({"name": "Company 2"})
        cls.journal_bank = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        cls.product = cls.env["product.product"].create(
            {"name": "Service 1", "type": "service"}
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
                "company_id": company.id,
                "tax_group_id": tax_group.id,
                "price_include": True,
            }
        )
        employee_home = cls.env["res.partner"].create({"name": "Employee Home Address"})
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Employee A", "address_home_id": employee_home.id}
        )
        advance_account = cls.env["account.account"].create(
            {
                "code": "154000",
                "name": "Employee Advance",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_current_assets"
                ).id,
                "reconcile": True,
            }
        )
        cls.account_sales = cls.env["account.account"].create(
            {
                "code": "X1020",
                "name": "Product Sales - (test)",
                "user_type_id": cls.env.ref("account.data_account_type_revenue").id,
            }
        )
        cls.emp_advance = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        cls.emp_advance.property_account_expense_id = advance_account
        # Create advance expense 1,000
        cls.advance = cls._create_expense_sheet(
            cls, "Advance 1,000", cls.employee, cls.emp_advance, 1000.0, advance=True
        )
        # Create clearing expense 1,000
        cls.clearing_equal = cls._create_expense_sheet(
            cls, "Buy service 1,000", cls.employee, cls.product, 1000.0
        )
        # Create clearing expense 1,200
        cls.clearing_more = cls._create_expense_sheet(
            cls, "Buy service 1,200", cls.employee, cls.product, 1200.0
        )
        # Create clearing expense 800
        cls.clearing_less = cls._create_expense_sheet(
            cls, "Buy service 800", cls.employee, cls.product, 800.0
        )

    def _create_expense(
        self,
        description,
        employee,
        product,
        amount,
        advance=False,
        payment_mode="own_account",
        account=False,
    ):
        with Form(
            self.env["hr.expense"].with_context(default_advance=advance)
        ) as expense:
            expense.name = description
            expense.employee_id = employee
            if not advance:
                expense.product_id = product
            expense.unit_amount = amount
            expense.payment_mode = payment_mode
            if account:
                expense.account_id = account
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
            f.journal_id = self.journal_bank
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
                self.employee,
                self.emp_advance,
                1.0,
                advance=True,
                account=self.account_sales,
            )
        # Advance Sheet should not have > 1 expense lines
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Buy service 1,000", self.employee, self.product, 1.0
            )
            self.advance.write({"expense_line_ids": [(4, expense.id)]})
        # Advance Expense's product, must not has tax involved
        with self.assertRaises(ValidationError):
            self.emp_advance.supplier_taxes_id |= self.tax
            expense = self._create_expense(
                "Advance 1,000", self.employee, self.emp_advance, 1.0, advance=True
            )
        self.emp_advance.supplier_taxes_id = False  # Remove tax bf proceed
        # Advance Expense, must not paid by company
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.employee,
                self.emp_advance,
                1.0,
                advance=True,
                payment_mode="company_account",
            )
        # Advance Expense, must be product advance only
        with self.assertRaises(ValidationError):
            expense = self._create_expense(
                "Advance 1,000",
                self.employee,
                self.emp_advance,
                1.0,
                advance=True,
            )
            expense.product_id = self.product.id
            expense._check_advance()
        # Advance Expense's product must have account configured
        with self.assertRaises(ValidationError):
            self.emp_advance.property_account_expense_id = False
            expense = self._create_expense(
                "Advance 1,000", self.employee, self.emp_advance, 1.0, advance=True
            )

    def test_1_clear_equal_advance(self):
        """When clear equal advance, all set"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.approve_expense_sheets()
        self.advance.action_sheet_move_create()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_id, 1000.0)
        self.assertEqual(self.advance.state, "done")
        # ------------------ Clearing --------------------------
        # Clear this with previous advance
        vals = self.advance.open_clear_advance()  # Test Clear Advance button
        ctx = vals.get("context")
        self.assertEqual(ctx["default_advance_sheet_id"], self.advance.id)
        self.clearing_equal.advance_sheet_id = self.advance
        self.assertEqual(self.clearing_equal.advance_sheet_residual, 1000.0)
        self.clearing_equal.action_submit_sheet()
        self.clearing_equal.approve_expense_sheets()
        self.clearing_equal.action_sheet_move_create()
        # Equal amount, state change to Paid and advance is cleared
        self.assertEqual(self.clearing_equal.state, "done")
        self.assertEqual(self.clearing_equal.advance_sheet_residual, 0.0)
        # Clear this with previous advance is done
        self.clearing_more.advance_sheet_id = self.advance
        with self.assertRaises(ValidationError):
            self.clearing_more.action_submit_sheet()
        # There are 2 clearing in advance
        self.assertEqual(self.advance.clearing_count, 2)
        # Check link clearing in advance must be equal clearing count
        clearing_dict = self.advance.action_open_clearings()
        self.assertEqual(
            len(clearing_dict["domain"][0][2]), self.advance.clearing_count
        )
        # Check advance from employee
        self.assertEqual(self.employee.advance_count, 1)
        clearing_document = self.employee.action_open_advance_clearing()
        self.assertEqual(
            len(clearing_document["domain"][0][2]), self.employee.advance_count
        )
        # Check back state move in advance after create clearing
        with self.assertRaises(UserError):
            self.advance.account_move_id.button_draft()
        with self.assertRaises(UserError):
            self.advance.account_move_id.button_cancel()
        with self.assertRaises(UserError):
            self.advance.account_move_id._reverse_moves()

    def test_2_clear_more_than_advance(self):
        """When clear more than advance, do pay more"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.approve_expense_sheets()
        self.advance.action_sheet_move_create()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_id, 1000.0)
        self.assertEqual(self.advance.state, "done")
        # ------------------ Clearing --------------------------
        # Clear this with previous advance
        self.clearing_more.advance_sheet_id = self.advance
        self.assertEqual(self.clearing_more.advance_sheet_residual, 1000.0)
        self.clearing_more.action_submit_sheet()
        self.clearing_more.approve_expense_sheets()
        self.clearing_more.action_sheet_move_create()
        # More amount, state not changed to paid, and has to pay 200 more
        self.assertEqual(self.clearing_more.state, "post")
        self.assertEqual(self.clearing_more.amount_payable, 200.0)
        self._register_payment(self.clearing_more.account_move_id, 200.0)
        self.assertEqual(self.clearing_more.state, "done")

    def test_3_clear_less_than_advance(self):
        """When clear less than advance, do return advance"""
        # ------------------ Advance --------------------------
        self.advance.action_submit_sheet()
        self.advance.approve_expense_sheets()
        self.advance.action_sheet_move_create()
        # Test return advance register payment with move state draft
        with self.assertRaises(UserError):
            self.advance.account_move_id.button_draft()
            self._register_payment(
                self.advance.account_move_id, 200.0, hr_return_advance=True
            )
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_id, 1000.0)
        self.assertEqual(self.advance.state, "done")
        # ------------------ Clearing, Return Advance --------------------------
        # Clear this with previous advance
        self.clearing_less.advance_sheet_id = self.advance
        self.assertEqual(self.clearing_less.advance_sheet_residual, 1000.0)
        self.clearing_less.action_submit_sheet()
        self.clearing_less.approve_expense_sheets()
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
                self.advance.account_move_id,
                300.0,
                ctx=register_payment["context"],
                hr_return_advance=True,
            )
        self.clearing_less.action_sheet_move_create()
        # Less amount, state set to done. Still remain 200 to be returned
        self.assertEqual(self.clearing_less.state, "done")
        self.assertEqual(self.clearing_less.advance_sheet_residual, 200.0)
        # Back to advance and do return advance, clearing residual become 0.0
        self._register_payment(
            self.advance.account_move_id,
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
        self.advance.expense_line_ids.clearing_product_id = self.product
        self.advance.action_submit_sheet()
        self.advance.approve_expense_sheets()
        self.advance.action_sheet_move_create()
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_id, 1000.0)
        self.assertEqual(self.advance.state, "done")
        # ------------------ Clearing --------------------------
        with Form(self.env["hr.expense.sheet"]) as sheet:
            sheet.name = "Test Clearing"
            sheet.employee_id = self.employee
        ex_sheet = sheet.save()
        ex_sheet.advance_sheet_id = self.advance
        self.assertEqual(len(ex_sheet.expense_line_ids), 0)
        ex_sheet._onchange_advance_sheet_id()
        self.assertEqual(len(ex_sheet.expense_line_ids), 1)
        reverse_move = self.advance.account_move_id._reverse_moves(cancel=True)
        self.assertNotEqual(reverse_move, self.advance.account_move_id)
