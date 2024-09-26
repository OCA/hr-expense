# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models


class HrAdvanceOverdueReminderWizard(models.TransientModel):
    _name = "hr.advance.overdue.reminder.wizard"
    _description = "Reminder Overdue Advance"

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        string="Employee(s)",
    )
    reminder_definition_id = fields.Many2one(
        comodel_name="reminder.definition",
        required=True,
    )
    reminder_number = fields.Integer(
        string="Reminder Every",
        required=True,
    )
    reminder_next_time = fields.Date(
        string="Next Reminder",
        compute="_compute_reminder_next_time",
        store=True,
        required=True,
        readonly=False,
    )
    reminder_type = fields.Selection(selection="_reminder_type_selection")
    mail_template_id = fields.Many2one(comodel_name="mail.template")
    letter_report = fields.Many2one(comodel_name="ir.actions.report")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.user.company_id.id,
    )
    create_activity = fields.Boolean()
    activity_type_id = fields.Many2one(
        comodel_name="mail.activity.type", string="Activity"
    )
    activity_summary = fields.Char(string="Summary")
    activity_note = fields.Html(string="Note")

    @api.depends("reminder_number")
    def _compute_reminder_next_time(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.reminder_next_time = today + relativedelta(days=rec.reminder_number)

    @api.model
    def _reminder_type_selection(self):
        return [("mail", _("E-mail")), ("letter", _("Letter"))]

    @api.onchange("reminder_definition_id")
    def onchange_reminder_definition(self):
        reminder = self.reminder_definition_id
        if reminder:
            self.write(
                {
                    "reminder_number": reminder.reminder_number or 0,
                    "company_id": reminder.company_id.id or self.env.company.id,
                    "reminder_type": reminder.reminder_type,
                    "mail_template_id": reminder.mail_template_id.id,
                    "letter_report": reminder.letter_report.id,
                    "create_activity": reminder.create_activity,
                    "activity_type_id": reminder.activity_type_id.id,
                    "activity_summary": reminder.activity_summary,
                    "activity_note": reminder.activity_note,
                }
            )

    def _prepare_reminder(self, date):
        ExpenseSheet = self.env["hr.expense.sheet"]
        active_ids = self._context.get("active_ids", False)
        vals = []
        for employee in self.employee_ids:
            expense_sheets = ExpenseSheet.search(
                [
                    ("id", "in", active_ids),
                    ("employee_id", "=", employee.id),
                ]
            )
            if not expense_sheets:
                continue
            vals.append(
                {
                    "employee_id": employee.id,
                    "user_id": self.env.user.id,
                    "expense_sheet_ids": [(6, 0, expense_sheets.ids)],
                    "company_id": self.company_id.id,
                    "reminder_type": self.reminder_type,
                    "reminder_next_time": self.reminder_next_time,
                    "mail_template_id": self.mail_template_id.id,
                    "letter_report": self.letter_report.id,
                    "create_activity": self.create_activity,
                    "activity_type_id": self.activity_type_id.id,
                    "activity_scheduled_date": self.create_activity
                    and self.reminder_next_time
                    or False,
                    "activity_summary": self.create_activity and self.activity_summary,
                    "activity_note": self.create_activity and self.activity_note,
                }
            )
        return vals

    def run(self):
        self.ensure_one()
        AdvanceOverdue = self.env["hr.advance.overdue.reminder"].sudo()
        today = self._context.get("manual_date", fields.Date.context_today(self))
        # Unlink data is not send yet
        existing_actions = AdvanceOverdue.search(
            [
                ("employee_id", "in", self.employee_ids.ids),
                ("state", "=", "draft"),
            ]
        )
        existing_actions.unlink()
        # Create new reminder
        vals = self._prepare_reminder(today)
        advance_overdue = AdvanceOverdue.create(vals)
        # Open new view overdue reminder
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "hr_expense_advance_overdue_reminder.action_hr_advance_overdue_reminder"
        )
        action["domain"] = [("id", "in", advance_overdue.ids)]
        return action
