# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Employee Advance and Clearing",
    "version": "19.0.1.0.0",
    "category": "Human Resources",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["hr_expense"],
    "external_dependencies": {"python": ["openupgradelib"]},
    "data": [
        "data/advance_product.xml",
        "views/account_payment_view.xml",
        "views/hr_expense_views.xml",
        "views/hr_employee_views.xml",
        "views/hr_employee_public_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "demo": ["demo/advance_account_demo.xml"],
    "installable": True,
    "maintainers": ["kittiu", "Saran440"],
}
