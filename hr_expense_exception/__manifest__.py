# Copyright 2021 Ecosoft <http://ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Expense Exception",
    "summary": "Custom exceptions on expense report",
    "version": "15.0.1.0.0",
    "category": "Human Resources",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["hr_expense", "base_exception"],
    "license": "AGPL-3",
    "data": [
        "security/ir.model.access.csv",
        "data/expense_sheet_exception_data.xml",
        "wizard/expense_sheet_exception_confirm_view.xml",
        "views/hr_expense_view.xml",
    ],
    "installable": True,
}
