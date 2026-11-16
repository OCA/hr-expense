# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    "name": "Expense Account",
    "summary": "Automatically create draft bills and attach PDF on expense approval",
    "version": "19.0.1.0.0",
    "author": "Odoo Community Association (OCA), glueckkanja AG",
    "maintainers": ["CRogos"],
    "license": "AGPL-3",
    "category": "Human Resources/Expenses",
    "depends": ["hr_expense"],
    "website": "https://github.com/OCA/hr-expense",
    "data": [
        "views/account_move_views.xml",
        "views/hr_expense_views.xml",
        "report/hr_expense_report.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_expense_account/static/src/views/list.xml",
        ],
    },
    "installable": True,
    "auto_install": False,
}
