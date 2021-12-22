# Copyright (C) 2021 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "HR Expense Analytic Distribution",
    "version": "14.0.1.0.1",
    "category": "Expense Management",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "depends": ["hr_expense"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_expense_distribution_views.xml",
        "views/hr_expense_sheet_views.xml",
    ],
    "installable": True,
    "maintainer": "dreispt",
    "development_status": "Beta",
}
