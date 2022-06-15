import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-hr-expense",
    description="Meta package for oca-hr-expense Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-hr_expense_advance_clearing',
        'odoo14-addon-hr_expense_advance_clearing_sequence',
        'odoo14-addon-hr_expense_analytic_distribution',
        'odoo14-addon-hr_expense_cancel',
        'odoo14-addon-hr_expense_exception',
        'odoo14-addon-hr_expense_invoice',
        'odoo14-addon-hr_expense_journal',
        'odoo14-addon-hr_expense_payment',
        'odoo14-addon-hr_expense_payment_widget_amount',
        'odoo14-addon-hr_expense_petty_cash',
        'odoo14-addon-hr_expense_sequence',
        'odoo14-addon-hr_expense_sequence_option',
        'odoo14-addon-hr_expense_tier_validation',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
