# Copyright 2023 ForgeFlow - Elmer García / Joan Solé
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Hr expense sheet tags",
    "version": "14.0.1.0.0",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": ["hr_expense", "crm"],
    "data": ["views/hr_expense_sheet.xml"],
    "pre_init_hook": "pre_init_hook",
    "installable": True,
}
