# Copyright 2023 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "HR Expense Advance to Vendor",
    "version": "15.0.1.0.0",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources",
    "depends": ["hr_expense_advance_clearing", "hr_expense_pay_to_vendor"],
    "data": [
        "data/advance_product.xml",
        "views/hr_expense_views.xml",
    ],
    "installable": True,
    "maintainers": ["ps-tubtim"],
}
