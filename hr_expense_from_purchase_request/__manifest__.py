# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Create Expenses from Purchase Request",
    "version": "14.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": ["hr_expense", "purchase_request"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_expense_views.xml",
        "views/purchase_request_views.xml",
    ],
    "installable": True,
    "maintainers": ["kittiu"],
}
