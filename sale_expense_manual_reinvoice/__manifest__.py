# Copyright 2021 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Sale Expense Manual Re-invoice",
    "summary": "Allow to manually re-invoice expenses",
    "version": "15.0.1.0.0",
    "author": "Camptocamp SA, Odoo Community Association (OCA)",
    "maintainers": ["ivantodorovich"],
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": ["sale_expense"],
    "data": [
        "views/account_analytic_line.xml",
        "views/hr_expense.xml",
        "views/product_template.xml",
    ],
}
