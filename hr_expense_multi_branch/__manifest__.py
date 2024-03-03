# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "HR Expense - Multi branch",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "category": "Human Resources",
    "summary": "Add branch on Expense",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["hr_expense", "account_multi_branch"],
    "data": [
        "views/hr_expense_views.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
