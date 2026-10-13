# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "HR Expense Tax Distribution",
    "summary": (
        "Allows to distribute a single expense amount across multiple tax rates "
        "by defining per-tax base amounts. Produces correct tax lines in the "
        "accounting entry when multiple VAT rates apply to the same receipt."
    ),
    "version": "18.0.1.0.0",
    "category": "Human Resources/Expenses",
    "website": "https://github.com/OCA/hr-expense",
    "author": "Akretion, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": ["hr_expense"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_expense_tax_distribution_views.xml",
    ],
    "installable": True,
    "development_status": "Beta",
    "maintainers": ["metaminux"],
}
