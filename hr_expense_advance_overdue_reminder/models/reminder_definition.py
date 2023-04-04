# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class ReminderDefinition(models.Model):
    _name = "reminder.definition"
    _description = "Reminder Definition"

    name = fields.Char(
        string="Description",
        required=True,
    )
    clearing_terms_days = fields.Integer(
        string="Clearing Terms",
        default=30,
        help="In case this field is configured, "
        "the system will help calculate Clearing Date Due according to the term.",
    )
    reminder_number = fields.Integer(string="Reminder Every", default=5)
    reminder_type = fields.Selection(
        selection="_reminder_type_selection",
        default="mail",
        string="Reminder",
        required=True,
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        default=lambda self: self.env.ref(
            "hr_expense_advance_overdue_reminder.email_template_overdue_reminder"
        ),
    )
    letter_report = fields.Many2one(comodel_name="ir.actions.report")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
    create_activity = fields.Boolean(
        help="If set, system will be notified reminder next time.",
    )
    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type", string="Activity"
    )
    activity_summary = fields.Char(string="Summary")
    activity_note = fields.Html(string="Note")

    @api.model
    def _reminder_type_selection(self):
        return [("mail", _("E-mail")), ("letter", _("Letter"))]
