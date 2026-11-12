# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import Command, api, fields, models
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
    is_overdue = fields.Boolean(
        compute="_compute_overdue",
        search="_search_is_overdue",
        string="Overdue",
    )
    overdue_days = fields.Integer(
        compute="_compute_overdue",
        string="Overdue (Days)",
    )
    clearing_date_due = fields.Date(
        string="Clearing Due Date",
        tracking=True,
        help="Estimated date for the expense to be cleared.",
    )

    @api.onchange("clearing_date_due")
    def _onchange_clearing_date_due(self):
        today = fields.Date.context_today(self)
        if self.clearing_date_due and self.clearing_date_due < today:
            raise UserError(
                self.env._("You can not select clearing due date less than today.")
            )

    def _get_date_overdue(self):
        """Hook for manual_date"""
        return fields.Date.context_today(self)

    @api.depends("state", "clearing_date_due", "clearing_residual")
    def _compute_overdue(self):
        date = self._get_date_overdue()
        for sheet in self:
            sheet.is_overdue = False
            sheet.overdue_days = 0

            # Check if the sheet is an advance,
            # has a clearing date due, and is not yet cleared
            if (
                sheet.clearing_date_due
                and sheet.clearing_date_due < date
                and sheet.clearing_residual > 0.0
            ):
                sheet.is_overdue = True
                sheet.overdue_days = (date - sheet.clearing_date_due).days

    def _search_is_overdue(self, operator, value):
        assert operator == "=" and value, "Operation not supported"
        return [
            ("clearing_date_due", "<", fields.Date.context_today(self)),
            ("clearing_residual", ">", 0.0),
        ]

    def action_sheet_move_post(self):
        reminder = self.env["reminder.definition"].search(
            [], order="overdue_days_min asc", limit=1
        )
        for sheet in self.filtered("advance"):
            if not sheet.clearing_date_due and not reminder:
                raise UserError(
                    self.env._(
                        "Please configured reminder definition before "
                        "Post Journal Entries"
                    )
                )

        res = super().action_sheet_move_post()

        for sheet in self.filtered(
            lambda sheet: sheet.advance and not sheet.clearing_date_due
        ):
            base_date = sheet.accounting_date or fields.Date.context_today(self)
            sheet.clearing_date_due = base_date + relativedelta(
                days=reminder.clearing_terms_days or 0
            )
        return res

    def _get_reminder(self, sheet, reminder_defs):
        return reminder_defs.filtered(
            lambda r: r.overdue_days_min <= sheet.overdue_days
        )[:1]

    def action_overdue_reminder(self):
        overdue_sheets = self.filtered("is_overdue")
        if len(overdue_sheets) != len(self):
            raise UserError(self.env._("You cannot remind non-overdue documents."))

        groups = defaultdict(lambda: self.env[self._name])
        reminder_defs = self.env["reminder.definition"].search(
            [], order="overdue_days_min desc"
        )

        for sheet in overdue_sheets:
            reminder = self._get_reminder(sheet, reminder_defs)
            if not reminder:
                continue

            key = (sheet.employee_id.id, reminder.id)
            groups[key] |= sheet

        vals = []
        for (employee_id, reminder_id), sheets in groups.items():
            vals.append(
                {
                    "employee_id": employee_id,
                    "reminder_definition_id": reminder_id,
                    "expense_sheet_ids": [Command.set(sheets.ids)],
                }
            )
        reminders = self.env["hr.advance.overdue.reminder"].create(vals)
        return {
            "name": self.env._("Advance Overdue Reminder"),
            "type": "ir.actions.act_window",
            "res_model": "hr.advance.overdue.reminder",
            "view_mode": "list,form",
            "domain": [("id", "in", reminders.ids)],
            "target": "current",
        }
