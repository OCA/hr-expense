# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo.addons.hr_expense_advance_clearing.tests.test_hr_expense_advance_clearing import (
    TestHrExpenseAdvanceClearing,
)


class TestHrExpenseAdvanceVendor(TestHrExpenseAdvanceClearing):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
