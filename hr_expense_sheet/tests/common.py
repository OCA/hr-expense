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
            account = cls._get_company_expense_account(company)
            if not company.expense_account_id:
                company.expense_account_id = account
            products.product_tmpl_id.with_company(company).write(
                {"property_account_expense_id": account.id}
            )
            cls.product_category.with_company(company).write(
                {"property_account_expense_categ_id": account.id}
            )
            journals = (
                cls.env["account.journal"]
                .with_company(company)
                .search(
                    [
                        *cls.env["account.journal"]._check_company_domain(company),
                        ("type", "=", "purchase"),
                    ]
                )
            )
            journals.filtered(
                lambda journal: not journal.default_account_id
            ).default_account_id = account

    @classmethod
    def _get_company_expense_account(cls, company):
        """Return an expense account that belongs to this company.

        Mexican charts mostly use ``expense_direct_cost``. Searching only
        ``expense`` leaves the receipt wizard without an account.
        """
        accounts = cls.env["account.account"].with_company(company)
        company_domain = accounts._check_company_domain(company)
        current = company.expense_account_id
        if current and current.filtered_domain(company_domain):
            return current
        account = accounts.search(
            [
                *company_domain,
                ("account_type", "in", ("expense", "expense_direct_cost")),
            ],
            limit=1,
        )
        if account:
            return account
        return accounts.create(
            {
                "name": "Test expense",
                "code": f"619{company.id:04d}",
                "account_type": "expense",
            }
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
        sheet = self.env["hr.expense.sheet"].create({**default_values, **values})
        account = self._get_company_expense_account(sheet.company_id)
        missing = sheet.expense_line_ids.filtered(lambda line: not line.account_id)
        if missing:
            missing.with_company(sheet.company_id).account_id = account
        return sheet
