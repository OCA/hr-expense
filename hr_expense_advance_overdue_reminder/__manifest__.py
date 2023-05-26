# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Employee Advance Overdue Reminder",
    "version": "15.0.1.0.0",
    "category": "Human Resources",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "Simple mail overdue employee advance reminder",
    "website": "https://github.com/OCA/hr-expense",
    "depends": [
        "hr_expense_advance_clearing_sequence",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "data/sequence_data.xml",
        "views/reminder_definition_view.xml",
        "views/hr_expense_views.xml",
        "views/hr_advance_overdue_view.xml",
        "wizard/hr_advance_overdue_reminder_wizard.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
