# Copyright 2020 Trinityroots Co., Ltd. (http://trinityroots.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Petty Cash",
    "version": "14.0.1.0.0",
    "category": "Human Resources",
    "author": "Trinityroots, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "website": "https://github.com/OCA/hr-expense",
    "depends": ["hr_expense"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_views.xml",
        "views/hr_expense_sheet_views.xml",
        "views/hr_expense_views.xml",
        "views/petty_cash_views.xml",
    ],
    "installable": True,
}
