# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    overdue_reminder_ids = fields.Many2many(
        comodel_name="hr.advance.overdue.reminder",
        relation="expense_sheet_overdue_reminder_rel",
        column1="expense_sheet_id",
        column2="overdue_reminder_id",
        string="Overdue Reminder Action History",
    )
    overdue_reminder_last_date = fields.Date(
        string="Last Reminder Date",
    )
    reminder_next_time = fields.Date(
        string="Next Reminder Date",
    )
    overdue_reminder_counter = fields.Integer(
        string="Reminder Count",
        compute="_compute_overdue_reminder",
        help="This counter is increased when reminder.",
    )
    is_overdue = fields.Boolean(
        compute="_compute_overdue",
    )
    clearing_date_due = fields.Date(
        string="Clearing Due Date",
        readonly=True,
        states={"draft": [("readonly", False)]},
        tracking=True,
    )

    @api.onchange("clearing_date_due")
    def _onchange_clearing_date_due(self):
        today = fields.Date.context_today(self)
        if self.clearing_date_due and self.clearing_date_due < today:
            raise UserError(_("You can not select clearing due date less than today."))

    @api.depends("state", "clearing_date_due")
    def _compute_overdue(self):
        date = self._context.get("manual_date", fields.Date.context_today(self))
        for sheet in self:
            sheet.is_overdue = False
            # Check if the sheet is an advance, has a clearing date due, and is not yet cleared
            if (
                sheet.advance
                and sheet.clearing_date_due
                and sheet.clearing_date_due < date
                and sheet.clearing_residual > 0.0
                and (not sheet.reminder_next_time or sheet.reminder_next_time < date)
            ):
                sheet.is_overdue = True

    @api.depends("overdue_reminder_ids")
    def _compute_overdue_reminder(self):
        for sheet in self:
            reminder = sheet.overdue_reminder_ids.filtered(lambda l: l.state == "done")
            sheet.overdue_reminder_counter = len(reminder)

    def action_sheet_move_create(self):
        res = super().action_sheet_move_create()
        reminder = self.env["reminder.definition"].search([], limit=1)
        for sheet in self.filtered("advance"):
            if not sheet.clearing_date_due:
                if not reminder:
                    raise UserError(
                        _(
                            "Please configured reminder definition before "
                            "Post Journal Entries"
                        )
                    )
                move_date = res[sheet.id].date
                sheet.clearing_date_due = move_date + relativedelta(
                    days=reminder.clearing_terms_days or 0.0
                )
        return res

    def action_overdue_reminder(self):
        if any(not sheet.is_overdue for sheet in self):
            raise UserError(_("You cannot remind this report."))
        employee_ids = self.mapped("employee_id.id")
        reminder = self.env["reminder.definition"].search([], limit=1)
        return {
            "name": _("New Advance Overdue"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.advance.overdue.reminder.wizard",
            "target": "new",
            "context": {
                "active_model": self._context.get("active_model", False),
                "active_ids": self._context.get("active_ids", False),
                "default_employee_ids": employee_ids,
                "default_reminder_definition_id": reminder.id,
            },
        }
