# Copyright 2024 Odoo Community Association (OCA)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Expense Trip",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Odoo Community Association (OCA)",
    "maintainers": ["CRogos"],
    "summary": "Add trip management to HR Expenses",
    "license": "LGPL-3",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["hr_expense"],
    "data": [
        "data/ir_sequence_data.xml",
        "security/hr_trip_security.xml",
        "security/ir.model.access.csv",
        "views/hr_trip_views.xml",
        "views/hr_expense_views.xml",
        "report/report_hr_trip.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "hr_expense_trip/static/src/views/*.js",
            "hr_expense_trip/static/src/views/trip_list_buttons.xml",
        ],
    },
}
