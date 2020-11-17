# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

logger = logging.getLogger(__name__)


class HrAdvanceOverdueReminderWizard(models.TransientModel):
    _name = "hr.advance.overdue.reminder.wizard"
    _inherit = "overdue.reminder.wizard"
    _description = "Reminder Overdue Advance"

    def _prepare_base_domain(self):
        base_domain = [
            ("company_id", "=", self.company_id.id),
            ("advance", "=", True),
            ("state", "=", "done"),
            ("clearing_residual", ">", 0.0),
            ("no_overdue_reminder", "=", False),
        ]
        return base_domain

    def _prepare_remind_trigger_domain(self, base_domain, date):
        domain = base_domain + [("clearing_date_due", "<", date)]
        if self.partner_ids:
            domain.append(("address_id", "in", self.partner_ids.ids))
        return domain

    def _prepare_reminder(self, base_domain, date):
        Partner = self.env["res.partner"]
        ExpenseSheet = self.env["hr.expense.sheet"]
        # overdue_sheet_ids = self._context.get("overdue_sheet_ids", False)
        partner_ids = self.partner_ids or Partner.search([])
        vals = []
        for partner in partner_ids:
            expense_sheet_ids = ExpenseSheet.search(
                base_domain
                + [
                    ("address_id", "=", partner.id),
                    ("clearing_date_due", "<", date),
                    # Check min interval
                    "|",
                    ("overdue_reminder_last_date", "=", False),
                    ("reminder_next_time", "<=", date),
                ]
            )
            # # Tree and Form
            # if overdue_sheet_ids:
            #     expense_sheet_ids = ExpenseSheet.browse(overdue_sheet_ids)
            #     expense_sheet_ids = expense_sheet_ids.filtered(
            #         lambda l: l.address_id.id == partner.id
            #         and not l.no_overdue_reminder
            #         and (
            #             not l.overdue_reminder_last_date
            #             or l.overdue_reminder_last_date <= min_interval_date
            #         )
            #     )
            if not expense_sheet_ids:
                continue
            vals.append(
                {
                    "partner_id": expense_sheet_ids[0].address_id.id,
                    "commercial_partner_id": partner.id,
                    "user_id": self.env.user.id,
                    "expense_sheet_ids": [(6, 0, expense_sheet_ids.ids)],
                    "company_id": self.company_id.id,
                    "reminder_type": self.reminder_type,
                    "reminder_next_time": self.reminder_next_time,
                    "mail_template_id": self.mail_template_id.id,
                    "attachment_letter": self.attachment_letter,
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
        AdvanceOverdue = self.env["hr.advance.overdue.reminder"]
        user_id = self.env.user.id
        today = self._context.get("manual_date", fields.Date.context_today(self))
        # Unlink data is not send yet
        existing_actions = AdvanceOverdue.search(
            [("user_id", "=", user_id), ("state", "=", "draft")]
        )
        existing_actions.unlink()
        base_domain = self._prepare_base_domain()
        vals = self._prepare_reminder(base_domain, today)
        advance_overdue = AdvanceOverdue.create(vals)
        xid = "hr_expense_advance_overdue_reminder.action_hr_advance_overdue_reminder"
        action = self.env.ref(xid).sudo().read()[0]
        action["domain"] = [("id", "in", advance_overdue.ids)]
        return action
