# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Expense Report Sub State",
    "version": "14.0.1.0.0",
    "category": "Tools",
    "author": "Ecosoft,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "depends": ["base_substate", "hr_expense"],
    "data": [
        "views/hr_expense_views.xml",
        "data/hr_expense_substate_mail_template_data.xml",
        "data/hr_expense_substate_data.xml",
    ],
    "demo": ["demo/hr_expense_substate_demo.xml"],
    "installable": True,
}
