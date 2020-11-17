# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class ReminderDefinition(models.Model):
    _inherit = "reminder.definition"

    clearing_terms_days = fields.Integer(string="Clearing Terms (days)", default=30)

    @api.model
    def _get_reminder_validation_model_names(self):
        res = super()._get_reminder_validation_model_names()
        res.append("hr.expense.sheet")
        return res

    @api.depends("model_id")
    def _compute_mail_template(self):
        res = super()._compute_mail_template()
        if self.model_id.model == "hr.expense.sheet":
            xmlid = (
                "hr_expense_advance_overdue_reminder"
                ".hr_advance_overdue_reminder_mail_template"
            )
            self.mail_template_id = self.env.ref(xmlid)
        return res
