# Copyright 2021 Camptocamp SA
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "HR Expense Report Payment Status",
    "summary": "Backport of the Payment Status (payment_state field) "
    "in Expense Report which is introduced in Odoo Community Version 15.0",
    "version": "14.0.1.0.0",
    "author": "Odoo SA, Odoo Community Association (OCA), Camptocamp",
    "license": "LGPL-3",
    "category": "Human Resources/Expenses",
    "depends": ["hr_expense"],
    "data": ["views/hr_expense_views.xml"],
    "website": "https://github.com/OCA/hr-expense",
    "installable": True,
}
