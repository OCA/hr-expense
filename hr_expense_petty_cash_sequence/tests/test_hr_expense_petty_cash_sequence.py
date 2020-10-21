# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import SavepointCase


class TestHrExpenseSequence(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_model = cls.env["account.account"]
        cls.move_model = cls.env["account.move"]
        cls.move_line_model = cls.env["account.move.line"]
        cls.journal_model = cls.env["account.journal"]
        cls.expense_model = cls.env["hr.expense"]
        cls.expense_sheet_model = cls.env["hr.expense.sheet"]
        cls.product = cls.env.ref("product.product_product_4")

        employee_home = cls.env["res.partner"].create({"name": "Employee Home Address"})
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Employee", "address_home_id": employee_home.id}
        )
        cls.account_payable_id = cls.account_model.create(
            {
                "code": "111111",
                "name": "Payable - Test",
                "user_type_id": cls.env.ref("account.data_account_type_payable").id,
                "reconcile": True,
            }
        )
        cls.petty_cash_account_id = cls.account_model.create(
            {
                "code": "000000",
                "name": "Petty Cash - Test",
                "user_type_id": cls.env.ref("account.data_account_type_liquidity").id,
            }
        )
        cls.petty_cash_holder = cls.env["petty.cash"].create(
            {
                "partner_id": employee_home.id,
                "account_id": cls.petty_cash_account_id.id,
                "petty_cash_limit": 1000.00,
            }
        )
        # Add Petty Cash Balance
        cls.purchase_journal = cls.journal_model.create(
            {"name": "purchase", "code": "P", "type": "purchase"}
        )
        move = cls.move_model.create(
            {
                "name": "purchase",
                "journal_id": cls.purchase_journal.id,
                "line_ids": [
                    (
                        0,
                        False,
                        {"credit": 1000.00, "account_id": cls.account_payable_id.id},
                    ),
                    (
                        0,
                        False,
                        {
                            "debit": 1000.00,
                            "account_id": cls.petty_cash_account_id.id,
                            "name": "Petty Cash",
                            "partner_id": employee_home.id,
                        },
                    ),
                ],
            }
        )
        move.post()

    def _create_expense_petty_cash(self):
        expense = self.env["hr.expense"].create(
            {
                "name": "Expense - Test",
                "employee_id": self.employee.id,
                "product_id": self.product.id,
                "unit_amount": 500.00,
                "payment_mode": "petty_cash",
                "petty_cash_id": self.petty_cash_holder.id,
            }
        )
        return expense

    def _create_expense_sheet(self, expense):
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Expense Report - Test",
                "employee_id": self.employee.id,
                "payment_mode": "petty_cash",
                "petty_cash_id": self.petty_cash_holder.id,
                "expense_line_ids": [(6, 0, [expense.id])],
            }
        )
        return expense_sheet

    def test_01_create_sequence_from_expense_or_report(self):
        """ Returns an open expense """
        expense = self._create_expense_petty_cash()
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Expense Report - Test",
                "employee_id": self.employee.id,
                "payment_mode": "petty_cash",
                "petty_cash_id": self.petty_cash_holder.id,
                "expense_line_ids": [(6, 0, [expense.id])],
            }
        )
        self.assertNotEqual(expense_sheet.number, "/", "Number create")

    def test_02_check_sequence_different(self):
        # Test number != '/'
        expense = self._create_expense_petty_cash()
        expense2 = self._create_expense_petty_cash()
        expense_sheet = self._create_expense_sheet(expense)
        self.assertNotEqual(expense_sheet.number, "/", "Number create")

        # Test number 1 != number 2
        expense_sheet2 = self._create_expense_sheet(expense2)
        sheet_number_1 = expense_sheet.number
        sheet_number_2 = expense_sheet2.number
        self.assertNotEqual(sheet_number_1, sheet_number_2, "Numbers are different")
