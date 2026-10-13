# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)


from odoo import Command, exceptions
from odoo.tests import Form, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpenseEmployeePayment(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.exp_emp_partner = cls.expense_employee.work_contact_id
        cls.exp_emp_partner_bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "1112223334",
                "partner_id": cls.exp_emp_partner.id,
                "acc_type": "bank",
            }
        )

    def _force_approve_with_draft_move(self, expense_sheet):
        """Force the approval of an expense and left
        the related move in draft state.
        This function allows to be compatible with other hr-expense modules."""
        if not expense_sheet.account_move_ids:
            expense_sheet.action_sheet_move_post()
            move = expense_sheet.account_move_ids
            if move.state == "posted":
                move.button_draft()

    def test_two_payments_one_expense_sheet(self):
        """Test paying one expense sheet with two payments"""
        # Create sheet and vendor bill
        expense_sheet = self.create_expense_report(
            {
                "name": "SHEET 2p 1e",
                "journal_id": self.company_data["default_journal_purchase"].id,
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "EXPENSE 2p 1e",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 100.00,
                        }
                    )
                ],
            }
        )
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        self._force_approve_with_draft_move(expense_sheet)
        # Select current Employee draft Bill and change to be a Vendor Bill
        vendor_bill = expense_sheet._get_vendor_moves(for_employee=True)
        vendor_bill.write({"partner_id": self.partner_a.id, "ref": "VB_01"})
        vendor_bill = expense_sheet._get_vendor_moves(for_employee=False)
        expense_sheet.action_sheet_move_post()
        self.assertTrue(vendor_bill)
        # Generate Payment Wizard
        action_data = expense_sheet.action_register_payment()
        # Check conciliation move exists
        conciliation_move = expense_sheet._get_conciliation_moves(posted=True)
        self.assertTrue(conciliation_move)
        # Check that the vendor payable move line is reconciled
        vendor_payable_move_line = expense_sheet._get_conciliation_payable_move_lines(
            for_employee=False
        )
        self.assertEqual(vendor_payable_move_line.reconciled, True)
        # Check that the employee payable move line is not reconciled
        employee_payable_move_line = expense_sheet._get_conciliation_payable_move_lines(
            for_employee=True
        )
        self.assertEqual(employee_payable_move_line.reconciled, False)
        # Check payment state on sheet is not paid
        self.assertEqual(expense_sheet.payment_state, "not_paid")
        # Pay 1
        with Form(
            self.env["account.payment.register"].with_context(**action_data["context"])
        ) as pay_form:
            self.assertEqual(
                pay_form.partner_bank_id, self.exp_emp_partner_bank_account
            )
            pay_form.amount = 60.00
            payment = pay_form.save()
            payment.action_create_payments()
        self.assertEqual(expense_sheet.payment_state, "partial")
        self.assertEqual(expense_sheet.amount_residual, 40.00)
        # Pay 2
        action_data = expense_sheet.action_register_payment()
        with Form(
            self.env["account.payment.register"].with_context(**action_data["context"])
        ) as pay_form:
            self.assertEqual(
                pay_form.partner_bank_id, self.exp_emp_partner_bank_account
            )
            self.assertEqual(pay_form.amount, 40.00)
            payment = pay_form.save()
            payment.action_create_payments()
        self.assertEqual(expense_sheet.payment_state, "paid")
        self.assertEqual(expense_sheet.amount_residual, 0.00)
        # Check that the employee payable move line is now reconciled
        self.assertEqual(employee_payable_move_line.reconciled, True)
        # Check that the vendor payable move line is still reconciled
        self.assertEqual(vendor_payable_move_line.reconciled, True)

    def test_one_payment_two_expense_sheets(self):
        """Test paying two expense sheets with one payment"""
        # Create sheet 1 and vendor bill
        expense_sheet1 = self.create_expense_report(
            {
                "name": "SHEET1 1p 2e",
                "journal_id": self.company_data["default_journal_purchase"].id,
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "EXPENSE1 1p 2e",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 100.00,
                        }
                    )
                ],
            }
        )
        expense_sheet1.action_submit_sheet()
        expense_sheet1.action_approve_expense_sheets()
        self._force_approve_with_draft_move(expense_sheet1)
        expense_sheet1._get_vendor_moves(for_employee=True).write(
            {"partner_id": self.partner_a.id, "ref": "VB_01"}
        )
        expense_sheet1.action_sheet_move_post()
        # Create sheet 2 and vendor bill
        expense_sheet2 = self.create_expense_report(
            {
                "name": "SHEET2 1p 2e",
                "journal_id": self.company_data["default_journal_purchase"].id,
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "EXPENSE2 1p 2e",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 200.00,
                        }
                    )
                ],
            }
        )
        expense_sheet2.action_submit_sheet()
        expense_sheet2.action_approve_expense_sheets()
        self._force_approve_with_draft_move(expense_sheet2)
        expense_sheet2._get_vendor_moves(for_employee=True).write(
            {"partner_id": self.partner_a.id, "ref": "VB_02"}
        )
        expense_sheet2.action_sheet_move_post()
        # Pay both sheets at once
        expense_sheets = expense_sheet1 | expense_sheet2
        action_data = expense_sheets.action_register_payment()
        with Form(
            self.env["account.payment.register"].with_context(**action_data["context"])
        ) as pay_form:
            self.assertEqual(
                pay_form.partner_bank_id, self.exp_emp_partner_bank_account
            )
            self.assertTrue(pay_form.group_payment)
            payment = pay_form.save()
            payment.action_create_payments()
        self.assertEqual(expense_sheet1.payment_state, "paid")
        self.assertEqual(expense_sheet2.payment_state, "paid")
        # Check that the employee payable move lines are now reconciled
        employee_payable_move_lines = (
            expense_sheets._get_conciliation_payable_move_lines(for_employee=True)
        )
        self.assertTrue(employee_payable_move_lines.mapped("reconciled"))
        # Check that the vendor payable move line is still reconciled
        vendor_payable_move_lines = expense_sheets._get_conciliation_payable_move_lines(
            for_employee=False
        )
        self.assertTrue(vendor_payable_move_lines.mapped("reconciled"))

    def test_unable_to_pay_employee_and_vendor_bill_at_the_same_time(self):
        """Test trying to pay a Vendor Expense Sheet and an
        Employee Expense Sheet at the same time"""
        # Create sheet 1 and vendor bill
        expense_sheet1 = self.create_expense_report(
            {
                "name": "SHEET1 1p 2e error",
                "journal_id": self.company_data["default_journal_purchase"].id,
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "EXPENSE1 1p 2e error",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 100.00,
                        }
                    )
                ],
            }
        )
        expense_sheet1.action_submit_sheet()
        expense_sheet1.action_approve_expense_sheets()
        self._force_approve_with_draft_move(expense_sheet1)
        expense_sheet1._get_vendor_moves(for_employee=True).write(
            {"partner_id": self.partner_a.id, "ref": "VB_01"}
        )
        expense_sheet1.action_sheet_move_post()
        # Create sheet 2 and employee bill
        expense_sheet2 = self.create_expense_report(
            {
                "name": "SHEET2 1p 2e error",
                "journal_id": self.company_data["default_journal_purchase"].id,
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "EXPENSE2 1p 2e error",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 200.00,
                        }
                    )
                ],
            }
        )
        expense_sheet2.action_submit_sheet()
        expense_sheet2.action_approve_expense_sheets()
        self._force_approve_with_draft_move(expense_sheet2)
        expense_sheet2.action_sheet_move_post()
        # Pay both sheets at once
        expense_sheets = expense_sheet1 | expense_sheet2
        with self.assertRaisesRegex(
            exceptions.UserError, "cannot register a payments for Employees and Vendors"
        ):
            expense_sheets.action_register_payment()

    def test_split_expense_sheet(self):
        """Test splitting an expense sheet with multiple lines into
        separate expense sheets with one line each"""
        # Create sheet with two lines
        expense_sheet = self.create_expense_report(
            {
                "name": "SPLIT SHEET",
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "SPLIT EXPENSE 1",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 100.00,
                        }
                    ),
                    Command.create(
                        {
                            "name": "SPLIT EXPENSE 2",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 200.00,
                        }
                    ),
                ],
            }
        )
        expense_sheet.action_submit_sheet()
        self.assertEqual(expense_sheet.state, "submit")
        # Split expense sheet
        action = expense_sheet._action_split_expenses()
        splitted_sheets = self.env["hr.expense.sheet"].search(action["domain"])
        self.assertEqual(len(splitted_sheets), 2)
        # State is preserved
        self.assertEqual(splitted_sheets.mapped("state"), ["submit", "submit"])

    def test_cannot_split_expense_sheet(self):
        """Test can't splitting an expense sheet if state is not allowed"""
        # Create sheet with two lines
        expense_sheet = self.create_expense_report(
            {
                "name": "SPLIT SHEET",
                "expense_line_ids": [
                    Command.create(
                        {
                            "name": "SPLIT EXPENSE 1",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 100.00,
                        }
                    ),
                    Command.create(
                        {
                            "name": "SPLIT EXPENSE 2",
                            "payment_mode": "own_account",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount": 200.00,
                        }
                    ),
                ],
            }
        )
        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        self._force_approve_with_draft_move(expense_sheet)
        # Split the sheet with raises
        with self.assertRaisesRegex(exceptions.UserError, "can be splitted"):
            expense_sheet._action_split_expenses()
