# Copyright 2023 ForgeFlow - Elmer García / Joan Solé
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Hr expense tag",
    "version": "14.0.1.0.0",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": ["hr_expense"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_expense.xml",
        "views/hr_expense_sheet.xml",
    ],
    "installable": True,
}
