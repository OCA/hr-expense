# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import Form, SavepointCase


class TestHrExpenseAdvanceClearingSequence(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.expense_sheet_model = cls.env["hr.expense.sheet"]
        cls.partner_1 = cls.env.ref("base.res_partner_12")
        cls.employee_1 = cls.env.ref("hr.employee_hne")
        cls.employee_1.address_home_id = cls.partner_1.id
        user_type_expense = cls.env.ref("account.data_account_type_expenses")
        account_expense = cls.env["account.account"].create(
            {
                "code": "NC1113",
                "name": "HR Expense - Test Purchase Account",
                "user_type_id": user_type_expense.id,
            }
        )
        cls.emp_advance = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        cls.emp_advance.property_account_expense_id = account_expense
        cls.expense = cls._create_expense(
            cls, "Advance 1,000", cls.employee_1, cls.emp_advance, 1000.0, advance=True
        )

        cls.sheet = cls._create_expense_sheet(
            cls, "Advance 1,000", cls.employee_1, cls.emp_advance, 1000.0, advance=True
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
        expense_sheet = self.expense_sheet_model.create(
            {
                "name": description,
                "advance": advance,
                "employee_id": expense.employee_id.id,
                "expense_line_ids": [(6, 0, [expense.id])],
            }
        )
        return expense_sheet

    def test_01_create_sequence_from_expense(self):
        # Test number != '/'
        advance_sheet = self.expense_sheet_model.create(
            {
                "name": "Advance 1,000",
                "advance": True,
                "employee_id": self.expense.employee_id.id,
                "expense_line_ids": [[4, self.expense.id, False]],
            }
        )
        self.assertNotEqual(advance_sheet.number, "/", "Number create")
        self.assertNotEqual(advance_sheet.number.find("AV"), -1)
        # Test number 1 != number 2
        self.assertNotEqual(
            advance_sheet.number, advance_sheet.copy().number, "Numbers are different"
        )

    def test_02_create_sequence_from_report(self):
        # Test number != '/'
        self.assertNotEqual(self.sheet.number, "/", "Number create")
        self.assertNotEqual(self.sheet.number.find("AV"), -1)
        # Test number 1 != number 2
        sheet_number_1 = self.sheet.number
        sheet2 = self.sheet.copy()
        sheet_number_2 = sheet2.number
        self.assertNotEqual(sheet_number_1, sheet_number_2, "Numbers are different")
