import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-hr-expense",
    description="Meta package for oca-hr-expense Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-hr_expense_advance_clearing>=16.0dev,<16.1dev',
        'odoo-addon-hr_expense_cancel>=16.0dev,<16.1dev',
        'odoo-addon-hr_expense_invoice>=16.0dev,<16.1dev',
        'odoo-addon-hr_expense_payment>=16.0dev,<16.1dev',
        'odoo-addon-hr_expense_sequence>=16.0dev,<16.1dev',
        'odoo-addon-hr_expense_tier_validation>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
