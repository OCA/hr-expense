# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

{
    "name": "Hr Expense - Employee Payment",
    "summary": "Allow to pay employees for expense Vendor Bills",
    "version": "18.0.1.0.0",
    "development_status": "Alpha",
    "category": "Human Resources/Expenses",
    "website": "https://github.com/OCA/hr-expense",
    "author": "Moduon, Odoo Community Association (OCA)",
    "maintainers": ["Shide", "rafaelbn"],
    "license": "LGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "hr_expense",
    ],
    "data": [
        "data/ir_actions_server.xml",
        "views/res_config_settings_views.xml",
    ],
}
