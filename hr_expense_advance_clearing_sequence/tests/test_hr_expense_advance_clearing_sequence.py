# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests import tagged

from odoo.addons.hr_expense_advance_clearing.tests.test_hr_expense_advance_clearing import (  # noqa: E501
    TestHrExpenseAdvanceClearing,
)


@tagged("-at_install", "post_install")
class TestHrExpenseAdvanceClearingSequence(TestHrExpenseAdvanceClearing):
    def test_advance_gets_AV_sequence_number(self):
        """Creating an advance expense fills `number` from the AV sequence."""
        advance = self._create_advance(500.0, "First advance")
        self.assertNotEqual(advance.number, "/")
        self.assertIn("AV", advance.number)
        advance2 = self._create_advance(500.0, "Second advance")
        self.assertNotEqual(advance.number, advance2.number)

    def test_advance_from_context_default_gets_AV_sequence_number(self):
        """An advance flagged only by the context default is numbered too."""
        advance = (
            self.env["hr.expense"]
            .with_context(default_advance=True)
            .create(
                {
                    "name": "advance from context",
                    "employee_id": self.expense_employee.id,
                    "product_id": self.advance_product.id,
                    "total_amount_currency": 500.0,
                    "payment_mode": "own_account",
                }
            )
        )
        self.assertTrue(advance.advance)
        self.assertIn("AV", advance.number)

    def test_advance_keeps_AV_sequence_under_a_sequence_option(self):
        """An active expense sequence option must not take over advance numbers."""
        if "ir.sequence.option" not in self.env:
            self.skipTest("base_sequence_option is not installed")
        option_sequence = self.env["ir.sequence"].create(
            {"name": "Expense option", "prefix": "OPT/", "padding": 4}
        )
        base = self.env["ir.sequence.option"].create(
            {
                "name": "Expense option",
                "model": "hr.expense",
                "use_sequence_option": True,
            }
        )
        self.env["ir.sequence.option.line"].create(
            {
                "base_id": base.id,
                "name": "every expense",
                "filter_domain": "[]",
                "sequence_id": option_sequence.id,
            }
        )
        advance = self._create_advance(500.0, "Advance under an option")
        self.assertIn("AV", advance.number)
        self.assertNotIn("OPT/", advance.number)

    def test_sequence_code_is_the_one_shipped_in_data(self):
        """The code looked up at create() is the code of the shipped record.

        The data file is `noupdate="1"`, so a database upgraded from 18.0
        keeps whatever code the record was created with; changing the string
        here would leave those databases without an advance sequence.
        """
        sequence = self.env.ref(
            "hr_expense_advance_clearing_sequence.seq_expense_advance"
        )
        self.assertEqual(sequence.code, "hr.expense.sheet.advance")
        self.assertTrue(
            self.env["ir.sequence"].next_by_code(sequence.code),
            "create() looks the sequence up by this code",
        )

    def test_regular_expense_uses_default_sequence(self):
        """A regular (non-advance) expense uses the standard hr.expense
        sequence (provided by hr_expense_sequence), not the advance one."""
        regular = self.env["hr.expense"].create(
            {
                "name": "regular",
                "employee_id": self.expense_employee.id,
                "product_id": self.product_a.id,
                "total_amount_currency": 100.0,
                "payment_mode": "own_account",
            }
        )
        self.assertNotIn("AV", regular.number or "")
