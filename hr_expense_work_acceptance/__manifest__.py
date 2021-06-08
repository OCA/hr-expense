# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Expense Work Acceptance",
    "version": "14.0.1.0.0",
    "category": "Human Resources",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["hr_expense", "purchase_work_acceptance"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/expense_views.xml",
        "views/res_config_settings_views.xml",
        "views/work_acceptance_views.xml",
    ],
    "maintainer": ["kittiu"],
    "installable": True,
    "development_status": "Alpha",
}
