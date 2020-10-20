import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-hr-expense",
    description="Meta package for oca-hr-expense Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-hr_expense_sequence',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
