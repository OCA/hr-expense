# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "HR Expense one2many widget",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": ["hr_expense"],
    "data": [
        "security/hr_expense_security.xml",
        "views/res_config_settings_views.xml",
        "views/hr_expense_views.xml",
    ],
    "installable": True,
    "maintainers": ["kittiu"],
}
