# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrAdvanceOverdueReminder(models.Model):
    _name = "hr.advance.overdue.reminder"
    _inherit = ["mail.thread", "base.reminder.mixin"]
    _description = "Hr Advance Overdue Reminder"
    _order = "name desc"

    expense_sheet_ids = fields.Many2many(
        comodel_name="hr.expense.sheet",
        relation="expense_sheet_overdue_reminder_rel",
        column1="overdue_reminder_id",
        column2="expense_sheet_id",
        string="Overdue Expense Advance Sheet",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    name = fields.Char(required=True, default="/", readonly=True, copy=False)
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        tracking=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    employee_email = fields.Char(
        related="employee_id.private_email",
        string="Email",
    )
    user_id = fields.Many2one(comodel_name="res.users", readonly=True)
    date = fields.Date(default=fields.Date.context_today, readonly=True)
    reminder_definition_id = fields.Many2one(
        comodel_name="reminder.definition",
        required=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    reminder_type = fields.Selection(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    reminder_next_time = fields.Date(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    mail_template_id = fields.Many2one(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    letter_report = fields.Many2one(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    create_activity = fields.Boolean(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    activity_type_id = fields.Many2one(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    activity_summary = fields.Char(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    activity_scheduled_date = fields.Date(
        string="Scheduled Date",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    activity_note = fields.Html(
        readonly=True,
        states={"draft": [("readonly", False)]},
    )
    activity_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned to",
        compute="_compute_activity_user",
        store=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("done", "Done"), ("cancel", "Cancelled")],
        default="draft",
        readonly=True,
        tracking=True,
    )

    @api.depends("create_activity", "employee_id")
    def _compute_activity_user(self):
        for rec in self:
            rec.activity_user_id = False
            if rec.create_activity:
                rec.activity_user_id = rec.employee_id.user_id.id

    @api.model
    def _reminder_type_selection(self):
        return [("mail", _("E-mail")), ("letter", _("Letter"))]

    @api.onchange("reminder_definition_id")
    def onchange_reminder_definition(self):
        reminder = self.reminder_definition_id
        if reminder:
            today = fields.Date.context_today(self)
            self.write(
                {
                    "reminder_type": reminder.reminder_type,
                    "reminder_next_time": today
                    + relativedelta(days=reminder.reminder_number),
                    "mail_template_id": reminder.mail_template_id.id,
                    "letter_report": reminder.letter_report.id,
                    "create_activity": reminder.create_activity,
                    "activity_type_id": reminder.activity_type_id.id,
                    "activity_summary": reminder.activity_summary,
                    "activity_note": reminder.activity_note,
                }
            )

    def print_letter(self):
        self.ensure_one()
        if self.letter_report.model != self._name:
            raise UserError(_("Letter report is not use in '{}'").format(self._name))
        action = self.letter_report.with_context(discard_logo_check=True).report_action(
            self
        )
        return action

    def unlink(self):
        """Not allow delete document when sent already."""
        if any(rec.state != "draft" for rec in self):
            raise UserError(
                _("You are attempting to delete a record that has already been sent.")
            )
        return super().unlink()

    def _get_report_base_filename(self):
        self.ensure_one()
        fname = "overdue_letter-%s" % self.employee_id.name.replace(" ", "_")
        return fname

    def _prepare_mail_activity(self):
        self.ensure_one()
        expense_sheet_model_id = self.env.ref("hr_expense.model_hr_expense_sheet").id
        vals = [
            {
                "activity_type_id": self.activity_type_id.id or False,
                "summary": self.activity_summary,
                "date_deadline": self.activity_scheduled_date,
                "user_id": self.activity_user_id.id,
                "note": self.activity_note,
                "res_id": sheet.id,
                "res_model_id": expense_sheet_model_id,
            }
            for sheet in self.expense_sheet_ids
        ]
        return vals

    def _get_mail_template(self):
        return "hr_expense_advance_overdue_reminder.email_template_overdue_reminder"

    def validate_mail(self):
        self.ensure_one()
        if self.employee_id.sudo().address_home_id.type == "private":
            raise UserError(_("You can not sent email with address private contact."))
        template = self.env.ref(self._get_mail_template(), raise_if_not_found=False)
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", False)
        ctx = dict(
            default_model="hr.advance.overdue.reminder",
            default_res_id=self.id,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_composition_mode="comment",
            custom_layout="mail.mail_notification_light",
            force_email=True,
            active_ids=self.ids,
        )
        return {
            "name": _("Compose Email"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": ctx,
        }

    @api.model
    def create(self, vals):
        if vals.get("number", "/") == "/":
            number = (
                self.env["ir.sequence"].next_by_code(
                    "advance.overdue.reminder.sequence"
                )
                or "/"
            )
            vals["name"] = number
        return super().create(vals)

    def _update_overdue_advance(self):
        self.ensure_one()
        self.expense_sheet_ids.write(
            {
                "overdue_reminder_last_date": self.date,
                "reminder_next_time": self.reminder_next_time,
            }
        )
        self.state = "done"
        self._create_activity()
        return False

    def _create_activity(self):
        self.ensure_one()
        MailActivity = self.env["mail.activity"]
        mail_activity = False
        if self.create_activity:
            mail_activity = MailActivity.create(self._prepare_mail_activity())
        return mail_activity

    def action_validate(self):
        self.ensure_one()
        if self.reminder_type == "mail":
            return self.validate_mail()
        action = self.print_letter()
        self._update_overdue_advance()
        return action

    def action_cancel(self):
        return self.write({"state": "cancel"})
