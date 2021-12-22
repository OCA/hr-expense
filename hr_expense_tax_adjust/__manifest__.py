# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Expense Tax Adjustment",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "summary": "Allow to edit tax amount on expenses",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "depends": ["hr_expense"],
    "category": "Human Resources/Expenses",
    "data": [
        "views/asset_backend.xml",
        "views/hr_expense_views.xml",
    ],
    "qweb": [
        "static/src/xml/tax_group.xml",
    ],
    "installable": True,
    "maintainers": ["ps-tubtim"],
    "development_status": "Alpha",
}
