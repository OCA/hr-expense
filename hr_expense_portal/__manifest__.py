# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "HR Expense Portal",
    "version": "15.0.1.0.0",
    "license": "AGPL-3",
    "category": "Generic Modules/Human Resources",
    "summary": "Show current expense in a website.",
    "author": "Open Source Integrators, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["sale_expense", "website"],
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/expense_template.xml",
    ],
    "installable": True,
}
