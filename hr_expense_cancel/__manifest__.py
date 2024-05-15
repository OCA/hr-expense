# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Hr expense cancel",
    "version": "17.0.1.0.2",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/hr-expense",
    "license": "AGPL-3",
    "category": "Human Resources",
    # The module hr_expense_payment function is to link the generated payments
    # with it's corresponding expense sheet.
    # So when you want to cancel payments associated to a expense_sheet,
    # you need to know which payments are related with your expense sheet.
    # And that information is not available by inheriting hr_expense alone,
    # we need the module
    "depends": ["hr_expense_payment"],
    "data": ["views/hr_expense_views.xml"],
    "installable": True,
}
