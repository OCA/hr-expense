# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


from odoo import api, fields, models
from odoo.exceptions import UserError


class HrAdvanceOverdueReminder(models.Model):
    _name = "hr.advance.overdue.reminder"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Hr Advance Overdue Reminder"
    _order = "name desc"

    name = fields.Char(required=True, default="/", readonly=True, copy=False)
    expense_sheet_ids = fields.Many2many(
        comodel_name="hr.expense.sheet",
        relation="expense_sheet_overdue_reminder_rel",
        column1="overdue_reminder_id",
        column2="expense_sheet_id",
        string="Overdue Expense Advance Sheet",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        tracking=True,
    )
    employee_work_email = fields.Char(
        compute="_compute_employee_work_email",
        store=True,
    )
    user_id = fields.Many2one(
        comodel_name="res.users",
        default=lambda self: self.env.user,
        tracking=True,
        string="Responsible",
    )
    date = fields.Date(default=fields.Date.context_today)
    reminder_definition_id = fields.Many2one(
        comodel_name="reminder.definition",
        required=True,
    )
    action_type = fields.Selection(
        related="reminder_definition_id.action_type",
        store=True,
    )
    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        compute="_compute_mail_template",
        store=True,
    )
    is_warning_duplicate = fields.Boolean(
        compute="_compute_is_warning_duplicate",
        store=True,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        readonly=True,
        required=True,
        default=lambda self: self.env.company,
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("submit", "Submit"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ],
        default="draft",
        readonly=True,
        tracking=True,
    )

    @api.depends("employee_id")
    def _compute_employee_work_email(self):
        for rec in self:
            rec.employee_work_email = rec.employee_id.work_email

    @api.depends("reminder_definition_id")
    def _compute_mail_template(self):
        for rec in self:
            rec.mail_template_id = rec.reminder_definition_id.mail_template_id

    @api.depends("employee_id", "expense_sheet_ids", "reminder_definition_id")
    def _compute_is_warning_duplicate(self):
        Reminder = self.env["hr.advance.overdue.reminder"]
        for rec in self:
            rec.is_warning_duplicate = False
            if not rec.expense_sheet_ids:
                continue

            domain = [
                ("state", "!=", "draft"),
                ("reminder_definition_id", "=", rec.reminder_definition_id.id),
                ("employee_id", "=", rec.employee_id.id),
                ("expense_sheet_ids", "in", rec.expense_sheet_ids.ids),
            ]
            if rec._origin:
                domain.append(("id", "!=", rec._origin.id))

            if Reminder.search(domain, limit=1):
                rec.is_warning_duplicate = True

    def unlink(self):
        """Not allow delete document when sent already."""
        if any(rec.state != "draft" for rec in self):
            raise UserError(
                self.env._("You can't delete document when state is not draft")
            )
        return super().unlink()

    def validate_mail(self):
        self.ensure_one()
        template = self.mail_template_id
        compose_form = self.env.ref("mail.email_compose_message_wizard_form", False)
        related_partners = self.employee_id._get_related_partners()
        ctx = dict(
            default_model="hr.advance.overdue.reminder",
            default_res_ids=self.ids,
            default_use_template=bool(template),
            default_template_id=template.id,
            default_partner_ids=related_partners.ids,
            default_composition_mode="comment",
            mark_overdue_as_sent=1,
        )
        return {
            "name": self.env._("Compose Email"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(compose_form.id, "form")],
            "view_id": compose_form.id,
            "target": "new",
            "context": ctx,
        }

    def action_submit(self):
        ir_sequence = self.env["ir.sequence"]
        for rec in self:
            if rec.name == "/":
                number = (
                    ir_sequence.next_by_code("advance.overdue.reminder.sequence") or "/"
                )
                rec.name = number
        return self.write({"state": "submit"})

    def action_validate(self):
        self.ensure_one()
        if self.action_type == "mail":
            return self.validate_mail()
        return

    def action_draft(self):
        return self.write({"state": "draft"})

    def action_cancel(self):
        return self.write({"state": "cancel"})

    @api.returns("mail.message", lambda value: value.id)
    def message_post(self, **kwargs):
        """Auto change state to done when send mail"""
        if self.env.context.get("mark_overdue_as_sent"):
            self.filtered(lambda o: o.state == "submit").with_context(
                tracking_disable=True
            ).write({"state": "done"})
        return super().message_post(**kwargs)
