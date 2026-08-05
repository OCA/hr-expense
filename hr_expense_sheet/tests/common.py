# Copyright 2026 Tecnativa - Víctor Martínez
from odoo import Command
from odoo.tools import mute_logger

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestHrExpenseSheetCommon(TestExpenseCommon):
    @classmethod
    @mute_logger("odoo.addons.account.models.chart_template")
    def setUpClass(cls):
        super().setUpClass()

    def create_expense_report(self, values=None):
        values = values or {}
        default_values = {
            "name": "Test Expense Report",
            "employee_id": self.expense_employee.id,
            "company_id": self.company_data["company"].id,
            "expense_line_ids": [
                Command.create(
                    {
                        "employee_id": self.expense_employee.id,
                        "product_id": self.product_c.id,
                        "total_amount_currency": 1000.00,
                        "tax_ids": [Command.set(self.tax_purchase_a.ids)],
                        "date": self.frozen_today,
                        "company_id": self.company_data["company"].id,
                        "currency_id": self.company_data["currency"].id,
                    }
                )
            ],
        }
        return self.env["hr.expense.sheet"].create({**default_values, **values})
