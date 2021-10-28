# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Request Flow for Expense",
    "version": "14.0.1.0.0",
    "category": "Tools",
    "website": "https://github.com/OCA/hr-expense",
    "summary": """
        This module adds to the request_flow the possibility to generate
        Expense Sheet from an Requests for Expense.
    """,
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["request_flow", "hr_expense"],
    "data": [
        "data/server_actions.xml",
        "views/request_views.xml",
        "views/hr_expense_views.xml",
    ],
    "demo": [
        "demo/request_category_data.xml",
    ],
    "application": False,
    "installable": True,
}
