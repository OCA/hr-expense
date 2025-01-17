# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo.tests import tagged

from odoo.addons.hr_expense_advance_clearing.tests.test_hr_expense_advance_clearing import (  # noqa: E501
    TestHrExpenseAdvanceClearing,
)


@tagged("-at_install", "post_install")
class TestHrExpenseAdvanceClearingSequence(TestHrExpenseAdvanceClearing):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_01_create_sequence_from_sheet(self):
        advance_sheet = self.advance
        self.assertNotEqual(advance_sheet.number, "/", "Number create")
        self.assertNotEqual(advance_sheet.number.find("AV"), -1)
        # Test duplicate advance, number should be different
        self.assertNotEqual(
            advance_sheet.number, advance_sheet.copy().number, "Numbers are different"
        )
