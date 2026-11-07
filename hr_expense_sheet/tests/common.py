# Copyright 2026 Tecnativa - Víctor Martínez
from odoo import Command
from odoo.tools import mute_logger

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestHrExpenseSheetCommon(TestExpenseCommon):
    @classmethod
    @mute_logger("odoo.addons.account.models.chart_template")
    def setUpClass(cls):
        super().setUpClass()
        companies = cls.env.company | cls.company_data_2["company"]
        products = cls.product_a | cls.product_b | cls.product_c
        for company in companies:
            account = company.expense_account_id or cls.env["account.account"].with_company(
                company
            ).search([("account_type", "=", "expense")], limit=1)
            if not account:
                continue
            if not company.expense_account_id:
                company.expense_account_id = account
            products.with_company(company).write(
                {"property_account_expense_id": account.id}
            )
            cls.product_category.with_company(company).property_account_expense_categ_id = (
                account
            )
            journals = cls.env["account.journal"].with_company(company).search(
                [
                    *cls.env["account.journal"]._check_company_domain(company),
                    ("type", "=", "purchase"),
                ]
            )
            journals.filtered(lambda journal: not journal.default_account_id).write(
                {"default_account_id": account.id}
            )

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
