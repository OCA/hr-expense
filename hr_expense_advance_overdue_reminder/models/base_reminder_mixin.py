# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models


class BaseReminderMixIn(models.AbstractModel):
    _name = "base.reminder.mixin"
    _description = "Mixin used in base model that reminder"

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
