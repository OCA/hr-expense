# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

payment_mode_list = {
    "own_account": "Employee (to reimburse)",
    "company_account": "Company",
}


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    no_overdue_reminder = fields.Boolean(
        string="Disable Reminder", default=False, track_visibility="onchange"
    )
    overdue_reminder_ids = fields.Many2many(
        comodel_name="hr.advance.overdue.reminder",
        relation="expense_sheet_overdue_reminder_rel",
        column1="expense_sheet_id",
        column2="overdue_reminder_id",
        string="Overdue Reminder Action History",
    )
    overdue_reminder_last_date = fields.Date(
        compute="_compute_overdue_reminder", string="Last Reminder Date", store=True,
    )
    overdue_reminder_counter = fields.Integer(
        string="Reminder Count",
        store=True,
        compute="_compute_overdue_reminder",
        help="This counter is increased when reminder.",
    )
    overdue = fields.Boolean(compute="_compute_overdue")
    date_due = fields.Date(string="Due Date", readonly=True)

    _sql_constraints = [
        (
            "counter_positive",
            "CHECK(overdue_reminder_counter >= 0)",
            "Overdue Invoice Counter must always be positive",
        )
    ]

    @api.depends("state", "date_due")
    def _compute_overdue(self):
        today = self._context.get("date", False) or fields.Date.context_today(self)
        for exp in self:
            exp.overdue = False
            if (
                exp.advance
                and exp.state == "done"
                and exp.date_due
                and exp.date_due < today
            ):
                exp.overdue = True

    @api.depends(
        "overdue_reminder_ids.date", "overdue_reminder_ids.reminder_type",
    )
    def _compute_overdue_reminder(self):
        for exp in self:
            reminder = exp.overdue_reminder_ids
            date = reminder and reminder[0].date or False
            counter = reminder and len(reminder) or False
            exp.overdue_reminder_last_date = date
            exp.overdue_reminder_counter = counter

    def action_sheet_move_create(self):
        res = super().action_sheet_move_create()
        reminder = self.env["reminder.definition"].search(
            [("model_id", "=", "hr.expense.sheet")]
        )
        for sheet in self:
            if res and sheet.advance:
                if not reminder:
                    raise UserError(
                        _(
                            "Please configured reminder definition before "
                            "Post Journal Entries"
                        )
                    )
                move_date = res[sheet.id].date
                sheet.date_due = move_date + relativedelta(
                    days=reminder.terms_date_due_days or 0.0
                )
        return res

    def get_payment_mode(self, payment_mode):
        self.ensure_one()
        return payment_mode_list[payment_mode]

    def action_overdue_reminder(self):
        today = self._context.get("date", False) or fields.Date.context_today(self)
        expense_not_overdue = self.filtered(
            lambda exp: not (
                exp.residual
                and exp.advance
                and exp.date_due < today
                and exp.state == "done"
            )
        )
        if expense_not_overdue:
            raise UserError(_("You cannot remind this report."))
        partner_ids = [expense.address_id.id for expense in self]
        return {
            "name": _("New Overdue Advance Letter"),
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "hr.advance.overdue.reminder.wizard",
            "target": "new",
            "context": {
                "active_model": self._context.get("active_model", False),
                "default_partner_ids": partner_ids,
                "overdue_sheet_ids": self._context.get("active_ids", False),
            },
        }
