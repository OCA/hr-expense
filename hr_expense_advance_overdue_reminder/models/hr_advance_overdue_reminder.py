# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrAdvanceOverdueReminder(models.Model):
    _name = "hr.advance.overdue.reminder"
    _inherit = ["mail.thread"]
    _description = "Hr Advance Overdue Reminder"
    _order = "name desc"

    expense_sheet_ids = fields.Many2many(
        comodel_name="hr.expense.sheet",
        relation="expense_sheet_overdue_reminder_rel",
        column1="overdue_reminder_id",
        column2="expense_sheet_id",
        string="Overdue Expense Advance Sheet",
        states={"done": [("readonly", True)]},
    )
    name = fields.Char(required=True, default="/", readonly=True, copy=False)
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        tracking=True,
        states={"done": [("readonly", True)]},
    )
    employee_email = fields.Char(
        related="employee_id.private_email",
        string="Email",
        readonly=True,
    )
    user_id = fields.Many2one(comodel_name="res.users", readonly=True)
    date = fields.Date(default=fields.Date.context_today, readonly=True)
    reminder_definition_id = fields.Many2one(
        comodel_name="reminder.definition",
        required=True,
        states={"done": [("readonly", True)]},
    )
    reminder_type = fields.Selection(
        selection="_reminder_type_selection",
        default="mail",
        required=True,
        states={"done": [("readonly", True)]},
    )
    reminder_next_time = fields.Date(
        states={"done": [("readonly", True)]},
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        states={"done": [("readonly", True)]},
    )
    letter_report = fields.Many2one(
        comodel_name="ir.actions.report",
        states={"done": [("readonly", True)]},
    )
    create_activity = fields.Boolean(
        states={"done": [("readonly", True)]},
    )
    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type",
        string="Activity",
    )
    activity_summary = fields.Char(string="Summary")
    activity_scheduled_date = fields.Date(string="Scheduled Date")
    activity_note = fields.Html(string="Note")
    activity_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Assigned to",
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        [("draft", "Draft"), ("cancel", "Cancelled"), ("done", "Done")],
        default="draft",
        readonly=True,
        tracking=True,
    )

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

    def _prepare_attach_letter(self):
        attachment_ids = []
        for sheet in self.expense_sheet_ids:
            if self.letter_report.report_type in ("qweb-html", "qweb-pdf"):
                result, report_format = self.letter_report._render_qweb_pdf([sheet.id])
            else:
                res = self.letter_report.render([sheet.id])
                if not res:
                    raise UserError(
                        _("Unsupported report type %s found.").format(
                            self.letter_report.report_type
                        )
                    )
                result, report_format = res
            # TODO in trunk, change return format to binary
            # to match message_post expected format
            result = base64.b64encode(result)
            filename = "{}.{}".format(self._get_report_base_filename(), report_format)
            attachment_ids.append([filename, result])
        return attachment_ids

    def _get_mail_template(self):
        return "hr_expense_advance_overdue_reminder.email_template_overdue_reminder"

    def validate_mail(self):
        self.ensure_one()
        if self.employee_id.address_home_id.type == "private":
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

    def _create_sequence(self):
        self.ensure_one()
        Sequence = self.env["ir.sequence"]
        sequence_code = "advance.overdue.reminder.sequence"
        if self.name == "/":
            self.name = (
                Sequence.with_context(ir_sequence_date=self.date).next_by_code(
                    sequence_code
                )
                or "/"
            )
        return True

    def _update_overdue_advance(self):
        self.expense_sheet_ids.write(
            {
                "overdue_reminder_last_date": self.date,
                "reminder_next_time": self.reminder_next_time,
            }
        )
        self.state = "done"
        self._create_activity()
        self._create_sequence()
        return False

    def _create_activity(self):
        MailActivity = self.env["mail.activity"]
        mail_activity = False
        if self.create_activity:
            mail_activity = MailActivity.create(self._prepare_mail_activity())
        return mail_activity

    def action_validate(self):
        self.ensure_one()
        action = True
        if self.reminder_type == "mail":
            return self.validate_mail()
        if self.reminder_type == "letter":
            action = self.print_letter()
        self._update_overdue_advance()
        return action

    def action_cancel(self):
        return self.write({"state": "cancel"})
