# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import UserError

logger = logging.getLogger(__name__)

MOD = "hr_expense_advance_overdue_reminder"


class HrAdvanceOverdueReminderWizard(models.TransientModel):
    _name = "hr.advance.overdue.reminder.wizard"
    _inherit = "overdue.reminder.wizard"
    _description = "Reminder Overdue Advance"

    def _prepare_base_domain(self):
        base_domain = [
            ("company_id", "=", self.company_id.id),
            ("advance", "=", True),
            ("state", "=", "done"),
            ("residual", ">", 0.0),
            ("no_overdue_reminder", "=", False),
        ]
        return base_domain

    def _prepare_remind_trigger_domain(self, base_domain, date):
        domain = base_domain + [("date_due", "<", date)]
        if self.partner_ids:
            domain.append(("address_id", "in", self.partner_ids.ids))
        return domain

    def _prepare_reminder(
        self, partner, base_domain, min_interval_date, sale_journals, date
    ):
        ExpenseSheet = self.env["hr.expense.sheet"]
        overdue_sheet_ids = self._context.get("overdue_sheet_ids", False)
        # Tree and Form
        if overdue_sheet_ids:
            expense_sheet_ids = ExpenseSheet.browse(overdue_sheet_ids)
            expense_sheet_ids = expense_sheet_ids.filtered(
                lambda l: l.address_id.id == partner.id
                and not l.no_overdue_reminder
                and (
                    not l.overdue_reminder_last_date
                    or l.overdue_reminder_last_date <= min_interval_date
                )
            )
        # Filter Direct
        else:
            expense_sheet_ids = ExpenseSheet.search(
                base_domain
                + [
                    ("address_id", "=", partner.id),
                    ("date_due", "<", date),
                    # Check min interval
                    "|",
                    ("overdue_reminder_last_date", "=", False),
                    ("overdue_reminder_last_date", "<=", min_interval_date),
                ]
            )
        if not expense_sheet_ids:
            return False
        next_scheduled = date + relativedelta(days=self.min_interval_days)
        vals = {
            "partner_id": expense_sheet_ids[0].address_id.id,
            "commercial_partner_id": partner.id,
            "user_id": self.env.user.id,
            "expense_sheet_ids": [(6, 0, expense_sheet_ids.ids)],
            "company_id": self.company_id.id,
            "reminder_type": self.reminder_type,
            "mail_template_id": self.mail_template_id.id,
            "attachment_letter": self.attachment_letter,
            "letter_report": self.letter_report.id,
            "create_activity": self.create_activity,
            "activity_scheduled_date": self.create_activity and next_scheduled or False,
            "activity_summary": self.create_activity and self.activity_summary,
            "activity_note": self.create_activity and self.activity_note,
        }
        return vals

    def run(self):
        self.ensure_one()
        if self.min_interval_days < 1:
            raise UserError(
                _("The minimum delay since last reminder must be strictly positive.")
            )
        Journal = self.env["account.journal"]
        Partner = self.env["res.partner"]
        ExpenseSheet = self.env["hr.expense.sheet"]
        AdvanceOverdue = self.env["hr.advance.overdue.reminder"]
        user_id = self.env.user.id
        existing_actions = AdvanceOverdue.search(
            [("user_id", "=", user_id), ("state", "=", "draft")]
        )
        existing_actions.unlink()
        purchase_journals = Journal.search(
            [("company_id", "=", self.company_id.id), ("type", "=", "purchase")]
        )
        today = self._context.get("date", False) or fields.Date.context_today(self)
        min_interval_date = today - relativedelta(days=self.min_interval_days)
        base_domain = self._prepare_base_domain()
        domain = self._prepare_remind_trigger_domain(base_domain, today)
        rg_res = ExpenseSheet.read_group(domain, ["address_id"], ["address_id"])
        action_ids = []
        for rg_re in rg_res:
            if rg_re["address_id"]:
                partner_id = rg_re["address_id"][0]
            partner = Partner.browse(partner_id)
            vals = self._prepare_reminder(
                partner, base_domain, min_interval_date, purchase_journals, today
            )
            if vals:
                action = AdvanceOverdue.create(vals)
                action_ids.append(action.id)
        if not action_ids:
            raise UserError(_("There are no overdue reminders."))
        xid = MOD + ".action_hr_advance_overdue_reminder"
        action = self.env.ref(xid).read()[0]
        action["domain"] = [("id", "in", action_ids)]
        return action
