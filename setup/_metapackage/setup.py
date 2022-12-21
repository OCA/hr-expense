import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-hr-expense",
    description="Meta package for oca-hr-expense Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-hr_expense_advance_clearing>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_cancel>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_exception>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_invoice>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_payment>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_petty_cash>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_portal>=15.0dev,<15.1dev',
        'odoo-addon-hr_expense_sequence>=15.0dev,<15.1dev',
        'odoo-addon-sale_expense_manual_reinvoice>=15.0dev,<15.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 15.0',
    ]
)
