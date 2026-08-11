# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ReminderDefinition(models.Model):
    _name = "reminder.definition"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Reminder Definition"

    name = fields.Char(
        string="Description",
        required=True,
    )
    clearing_terms_days = fields.Integer(
        string="Clearing Due Terms",
        default=7,
        help="Number of days used to calculate the Clearing Due Date "
        "when the user does not specify one manually.",
    )
    overdue_days_min = fields.Integer(
        help="Minimum overdue days to apply this reminder rule.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    action_type = fields.Selection(
        selection=[("mail", "E-mail")],
        default="mail",
        required=True,
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        default=lambda self: self._get_default_mail_template_id(),
    )

    def _get_default_mail_template_id(self):
        return self.env.ref(
            "hr_expense_advance_overdue_reminder.mail_template_hr_expense_advance_overdue_reminder",
            raise_if_not_found=False,
        )
