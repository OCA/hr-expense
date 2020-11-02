import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo13-addons-oca-hr-expense",
    description="Meta package for oca-hr-expense Odoo addons",
    version=version,
    install_requires=[
        'odoo13-addon-hr_expense_advance_clearing',
        'odoo13-addon-hr_expense_cancel',
        'odoo13-addon-hr_expense_invoice',
        'odoo13-addon-hr_expense_payment_difference',
        'odoo13-addon-hr_expense_petty_cash',
        'odoo13-addon-hr_expense_sequence',
        'odoo13-addon-hr_expense_tier_validation',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
