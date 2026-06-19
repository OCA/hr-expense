# Copyright 2014 Serv. Tecnol. Avanzados (http://www.serviciosbaeza.com)
#                       Pedro M. Baeza <pedro.baeza@serviciosbaeza.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestHrExpenseSequence(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_model = cls.env["hr.expense"]
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test expense product",
                "standard_price": 10.0,
                "list_price": 10.0,
                "can_be_expensed": True,
            }
        )
        cls.employee = cls.env["hr.employee"].create({"name": "Employee"})

    def _create_expense(self, name="Expense", **kwargs):
        vals = {
            "name": name,
            "employee_id": self.employee.id,
            "product_id": self.product.id,
            "total_amount_currency": self.product.standard_price or 10.0,
            "quantity": 1,
        }
        vals.update(kwargs)
        return self.expense_model.create(vals)

    def test_create_sequence_auto(self):
        """Expense created without an explicit number gets an auto-assigned one."""
        expense = self._create_expense("Expense Auto")
        self.assertNotEqual(expense.number, "/")
        self.assertTrue(expense.number)

    def test_create_sequence_slash_marker(self):
        """Expense created with explicit '/' also gets auto-assigned."""
        expense = self._create_expense("Expense Slash", number="/")
        self.assertNotEqual(expense.number, "/")

    def test_create_sequence_manual_override(self):
        """Caller can pass a specific number which is kept as-is."""
        expense = self._create_expense("Expense Manual", number="EX1")
        self.assertEqual(expense.number, "EX1")

    def test_sequence_code_is_the_one_shipped_in_data(self):
        """The code looked up at create() is the code of the shipped record.

        The data file is `noupdate="1"`, so a database upgraded from 18.0
        keeps whatever code the record was created with; changing the string
        here would leave those databases without an expense sequence, and
        every expense would keep the "/" placeholder.
        """
        sequence = self.env.ref("hr_expense_sequence.seq_expense")
        self.assertEqual(sequence.code, "hr.expense.sheet")
        self.assertTrue(
            self.env["ir.sequence"].next_by_code(sequence.code),
            "create() looks the sequence up by this code",
        )

    def test_copy_assigns_new_sequence(self):
        """Duplicating an expense draws a fresh sequence number."""
        expense = self._create_expense("Expense Copy Source")
        first_number = expense.number
        copy = expense.copy()
        self.assertNotEqual(copy.number, first_number)
        self.assertNotEqual(copy.number, "/")
