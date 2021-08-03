# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Request Flow for Advance",
    "version": "14.0.1.0.0",
    "category": "Tools",
    "website": "https://github.com/OCA/hr-expense",
    "summary": """
        This module adds to the request_flow workflow the possibility to generate
        Advance Sheet from an Requests for Advance.
    """,
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["hr_expense_request_flow", "hr_expense_advance_clearing"],
    "data": [
        "data/server_actions.xml",
        "views/request_views.xml",
        "views/request_category_views.xml",
        "views/hr_expense_view.xml",
    ],
    "demo": [
        "demo/request_category_data.xml",
    ],
    "application": False,
    "installable": True,
}
