# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)


from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestHrExpenseEmployeePayment(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_one_expense_two_payments(self):
        """Test paying one expense with two payment"""
        # Create and submit expense
        expense = self.create_expenses([{"payment_mode": "own_account"}])
        self.assertEqual(expense.state, "draft")
        expense.action_submit()
        self.assertEqual(expense.state, "submitted")
        expense.action_approve()
        self.assertEqual(expense.state, "approved")
        # Create Expense Vendor Bill
        self.post_expenses_with_wizard(expense)
        self.assertEqual(expense.account_move_id.state, "posted")
        # Change Vendor Bill to in_invoice
        expense.account_move_id.button_draft()
        expense.account_move_id.move_type = "in_invoice"
        expense.account_move_id.partner_id = self.partner_a.id
        expense.account_move_id.action_post()
        self.assertEqual(expense.account_move_id.state, "posted")
        self.assertEqual(expense.state, "posted")
        # Generate Conciliation Entry, but don't pay yet
        expense.account_move_id.action_register_payment()
        self.assertTrue(expense.conciliation_move_id)
        self.assertEqual(expense.state, "in_payment")
        # Check vendor Bill has been reconciled with the conciliation entry
        vendor_payable_move_line = expense._get_conciliation_payable_move_lines(
            for_employee=False
        )
        self.assertTrue(vendor_payable_move_line.reconciled)
        # Pay from Expense: Payment 1
        payment_wizard_action = expense.action_pay_employee()
        payment_wizard = (
            self.env[payment_wizard_action["res_model"]]
            .with_context(**payment_wizard_action["context"])
            .create(
                {
                    "amount": 600.0,
                    "journal_id": self.company_data["default_journal_bank"].id,
                }
            )
        )
        self.assertEqual(
            payment_wizard.partner_bank_id,
            self.expense_employee.sudo().bank_account_ids,
        )
        payment_wizard.action_create_payments()
        self.assertEqual(expense.state, "in_payment")
        # Pay from Expense: Payment 2
        payment_wizard_action = expense.action_pay_employee()
        payment_wizard = (
            self.env[payment_wizard_action["res_model"]]
            .with_context(**payment_wizard_action["context"])
            .create(
                {
                    "amount": 400.0,
                    "journal_id": self.company_data["default_journal_bank"].id,
                }
            )
        )
        self.assertEqual(
            payment_wizard.partner_bank_id,
            self.expense_employee.sudo().bank_account_ids,
        )
        payment_wizard.action_create_payments()
        self.assertEqual(expense.state, "paid")

    def test_pay_expense_and_vendor_bill(self):
        """Test paying one expense with two payment"""
        # Create and submit expense
        expense = self.create_expenses([{"payment_mode": "own_account"}])
        expense.action_submit()
        expense.action_approve()
        # Create Expense Vendor Bill
        self.post_expenses_with_wizard(expense)
        # Change Vendor Bill to in_invoice
        expense.account_move_id.button_draft()
        expense.account_move_id.move_type = "in_invoice"
        expense.account_move_id.partner_id = self.partner_a.id
        expense.account_move_id.action_post()
        self.assertEqual(expense.account_move_id.state, "posted")
        self.assertEqual(expense.state, "posted")
        # Create normal Bill (no Expense)
        normal_bill = self.init_invoice(
            "in_invoice",
            partner=self.partner_a,
            products=[self.product_a],
            # amounts=[600.0],
            post=True,
        )
        # Pay both Bills at once
        payment_wizard_action = (
            expense.account_move_id | normal_bill
        ).action_force_register_payment()
        payment_wizard = (
            self.env[payment_wizard_action["res_model"]]
            .with_context(**payment_wizard_action["context"])
            .create(
                {
                    "amount": normal_bill.amount_total + expense.total_amount,
                    "journal_id": self.company_data["default_journal_bank"].id,
                }
            )
        )
        payment_wizard.action_create_payments()
        # Check Expense
        self.assertEqual(expense.state, "paid")
        self.assertTrue(expense.conciliation_move_id)
        expense_vendor_payable_move_line = expense._get_conciliation_payable_move_lines(
            for_employee=False
        )
        self.assertTrue(expense_vendor_payable_move_line.reconciled)
        expense_employee_payable_move_line = (
            expense._get_conciliation_payable_move_lines(for_employee=True)
        )
        self.assertTrue(expense_employee_payable_move_line.reconciled)
        # Check normal Bill
        normal_bill_payable_move_line = normal_bill.line_ids.filtered_domain(
            [
                ("display_type", "=", "payment_term"),
            ]
        )
        self.assertTrue(normal_bill_payable_move_line.reconciled)
        # Check Bills and Expenses are not conciliated between each other
        self.assertEqual(
            len(
                expense_employee_payable_move_line.full_reconcile_id
                | expense_vendor_payable_move_line.full_reconcile_id
                | normal_bill_payable_move_line.full_reconcile_id
            ),
            3,
        )
