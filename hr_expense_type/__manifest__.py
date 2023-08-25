# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "HR Expense Type",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": ["hr_expense"],
    "website": "https://github.com/OCA/hr-expense",
    "data": [
        "security/ir.model.access.csv",
        "data/hr_expense_type_data.xml",
        "views/view_hr_expense_type.xml",
        "views/hr_expense_view.xml",
    ],
    "installable": True,
}
