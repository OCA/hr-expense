# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    "name": "Overdue Employee Advance Reminder",
    "version": "14.0.1.0.0",
    "category": "Human Resources",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "summary": "Simple mail overdue employee advance reminder",
    "website": "https://github.com/OCA/hr-expense",
    "depends": [
        "base_overdue_reminder",
        "hr_expense_advance_clearing",
        "hr_expense_advance_clearing_sequence",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/reminder_definition_view.xml",
        "data/sequence_data.xml",
        "data/mail_template.xml",
        "wizard/hr_advance_overdue_reminder_wizard.xml",
        "views/hr_advance_overdue_view.xml",
        "views/hr_expense_views.xml",
    ],
    "installable": True,
    "maintainers": ["Saran440"],
}
