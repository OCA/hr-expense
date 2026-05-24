# Copyright 2024 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "HR Expense Trip",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["hr_expense", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_trip_views.xml",
        "views/hr_expense_views.xml",
        "views/report_hr_trip.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "assets": {
        "web.assets_backend": [
            "hr_expense_trip/static/src/views/*.js",
        ],
    },
}
