# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import common
from odoo.tests.common import Form


class TestHrExpenseAdvanceClearingDetails(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.ref("base.main_company")
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
            }
        )
        employee_home = cls.env["res.partner"].create({"name": "Employee Home Address"})
        # Create User
        group_ids = cls.env.ref("base.group_system").ids
        cls.test_user_1 = cls.env["res.users"].create(
            {"name": "John", "login": "test1", "groups_id": [(6, 0, group_ids)]}
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee A",
                "address_home_id": employee_home.id,
                "user_id": cls.test_user_1.id,
            }
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
        cls.emp_advance = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        cls.emp_advance.property_account_expense_id = advance_account

    def _create_expense(
        self,
        description,
        employee,
        product,
        amount,
        advance=False,
        payment_mode="own_account",
        advance_line=0,
    ):
        if advance:
            details_list = [
                (
                    0,
                    0,
                    {
                        "name": "description %s" % line,
                        "unit_amount": amount / advance_line,
                    },
                )
                for line in range(advance_line)
            ]
            expense = self.env["hr.expense"].create(
                {
                    "advance": advance,
                    "name": description,
                    "employee_id": employee.id,
                    "product_id": product.id,
                    "account_id": self.emp_advance.property_account_expense_id.id,
                    "unit_amount": amount,
                    "payment_mode": payment_mode,
                    "tax_ids": False,
                    "advance_line": details_list,
                }
            )
        else:
            with Form(self.env["hr.expense"]) as expense:
                expense.advance = advance
                expense.name = description
                expense.employee_id = employee
                expense.product_id = product
                expense.unit_amount = amount
                expense.payment_mode = payment_mode
            expense = expense.save()
            expense.tax_ids = False  # Test no vat
        return expense

    def _create_expense_sheet(
        self, description, employee, product, amount, advance=False
    ):
        expense = self._create_expense(description, employee, product, amount, advance)
        # Add expense to expense sheet
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": description,
                "employee_id": expense.employee_id.id,
                "expense_line_ids": [(6, 0, [expense.id])],
            }
        )
        return expense_sheet

    def _register_payment(self, move_id, hr_return_advance=False):
        ctx = {
            "active_ids": [move_id.id],
            "active_id": move_id.id,
            "hr_return_advance": hr_return_advance,
            "active_model": "account.move",
        }
        PaymentWizard = self.env["account.payment.register"]
        with Form(PaymentWizard.with_context(ctx)) as f:
            f.journal_id = self.journal_bank
        payment_wizard = f.save()
        payment_wizard.action_create_payments()

    def test_01_clear_advance(self):
        # Create advance expense no details
        with self.assertRaises(UserError):
            advance_expense = self._create_expense(
                "Advance 1,000", self.employee, self.emp_advance, 1000.0, advance=True
            )
        # ------------------ Advance --------------------------
        advance_expense = self._create_expense(
            "Advance 1,000",
            self.employee,
            self.emp_advance,
            1000.0,
            advance=True,
            advance_line=2,
        )
        self.assertEqual(len(advance_expense.advance_line), 2)
        res = advance_expense.action_submit_expenses()
        advance_sheet = self.env[res.get("res_model")].browse(res.get("res_id"))
        self.assertTrue(advance_sheet.advance)
        self.assertEqual(len(advance_sheet.advance_line), 2)
        self.assertEqual(len(advance_sheet.clearing_line), 0)
        advance_sheet.approve_expense_sheets()
        advance_sheet.action_sheet_move_create()
        self.assertEqual(advance_sheet.clearing_residual, 1000.0)
        self._register_payment(advance_sheet.account_move_id)
        self.assertEqual(advance_sheet.state, "done")
        # ------------------ Clearing --------------------------
        # Clear this with previous advance
        vals = advance_sheet.open_clear_advance()  # Test Clear Advance button
        ctx = vals.get("context")
        self.assertEqual(ctx["default_advance_sheet_id"], advance_sheet.id)
        # Create clearing expense 1,000
        clearing_equal = self._create_expense_sheet(
            "Buy service 1,000", self.employee, self.product, 1000.0
        )
        clearing_equal.advance_sheet_id = advance_sheet.id
        self.assertEqual(clearing_equal.advance_sheet_residual, 1000.0)
        clearing_equal.action_submit_sheet()
        clearing_equal.approve_expense_sheets()
        clearing_equal.action_sheet_move_create()
        # Equal amount, state change to Paid and advance is cleared
        self.assertEqual(clearing_equal.state, "done")
        self.assertEqual(clearing_equal.advance_sheet_residual, 0.0)
        # Check details on advance and clearing
        self.assertEqual(len(advance_sheet.advance_line), 2)
        self.assertEqual(len(advance_sheet.clearing_line), 1)
        self.assertEqual(len(clearing_equal.advance_line), 2)
        self.assertEqual(len(clearing_equal.clearing_line), 0)
