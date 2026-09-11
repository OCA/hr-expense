# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Hr expense sheet",
    "version": "19.0.1.0.0",
    "author": "Odoo, Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources/Expenses",
    "depends": ["hr_expense"],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "data/mail_activity_type_data.xml",
        "data/mail_message_subtype_data.xml",
        "report/hr_expense_report.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "views/hr_expense_sheet_views.xml",
        "views/hr_expense_views.xml",
        "views/hr_department_views.xml",
        "views/mail_activity_views.xml",
    ],
    "demo": ["demo/hr_expense_demo.xml"],
    "assets": {
        "web.assets_backend": [
            "hr_expense_sheet/static/src/components/*.esm.js",
            "hr_expense_sheet/static/src/views/*.esm.js",
            "hr_expense_sheet/static/src/views/*.xml",
            "hr_expense_sheet/static/src/js/web/*.esm.js",
        ],
        "web.assets_tests": [
            "hr_expense_sheet/static/tests/tours/**/*",
        ],
    },
    "installable": True,
    "pre_init_hook": "pre_init_hook",
    "maintainers": ["victoralmau"],
}
