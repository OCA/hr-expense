# Copyright 2022 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Hr Expense Advance Clearing Consolidation",
    "summary": """
        HR Expense Advance Clearing Consolidation""",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "depends": [
        "hr_expense_advance_clearing",
        "account_reconciliation_widget",
    ],
    "data": [
        "views/hr_expense_sheet_view.xml",
    ],
}
