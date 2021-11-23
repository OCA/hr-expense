# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("post_install", "-at_install")
class TestExpenses(TestExpenseCommon):
    def test_expense_sheet_payment_state(self):
        """Test expense sheet payment states when partially paid, in payment and paid."""

        def get_payment(expense_sheet, amount):
            ctx = {
                "active_model": "account.move",
                "active_ids": expense_sheet.account_move_id.ids,
            }
            payment_register = (
                self.env["account.payment.register"]
                .with_context(**ctx)
                .create(
                    {
                        "amount": amount,
                        "journal_id": self.company_data["default_journal_bank"].id,
                        "payment_method_id": self.env.ref(
                            "account.account_payment_method_manual_in"
                        ).id,
                    }
                )
            )
            return payment_register._create_payments()

        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Expense for John Smith",
                "employee_id": self.expense_employee.id,
                "accounting_date": "2021-01-01",
                "expense_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "Car Travel Expenses",
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_a.id,
                            "unit_amount": 350.00,
                        },
                    )
                ],
            }
        )

        expense_sheet.action_submit_sheet()
        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        payment = get_payment(expense_sheet, 100.0)
        liquidity_lines1 = payment._seek_for_lines()[0]

        self.assertEqual(
            expense_sheet.payment_state,
            "partial",
            "payment_state should be partial",
        )

        payment = get_payment(expense_sheet, 250.0)
        liquidity_lines2 = payment._seek_for_lines()[0]

        in_payment_state = expense_sheet.account_move_id._get_invoice_in_payment_state()

        self.assertEqual(
            expense_sheet.payment_state,
            in_payment_state,
            "payment_state should be " + in_payment_state,
        )

        statement = self.env["account.bank.statement"].create(
            {
                "name": "test_statement",
                "journal_id": self.company_data["default_journal_bank"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "payment_ref": "pay_ref",
                            "amount": -350.0,
                            "partner_id": self.expense_employee.address_home_id.id,
                        },
                    )
                ],
            }
        )
        statement.button_post()
        statement.line_ids.reconcile(
            [{"id": liquidity_lines1.id}, {"id": liquidity_lines2.id}]
        )

        self.assertEqual(
            expense_sheet.payment_state, "paid", "payment_state should be paid"
        )
