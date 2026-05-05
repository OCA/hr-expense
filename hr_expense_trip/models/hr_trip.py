# Copyright 2024 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import base64

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HrTrip(models.Model):
    _name = "hr.trip"
    _description = "HR Trip"
    _order = "start_date desc, name"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]

    name = fields.Char(required=True)
    start_date = fields.Date(required=True)
    end_date = fields.Date(required=True)
    reason = fields.Text()
    partner_id = fields.Many2one(
        comodel_name="res.partner",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        default=lambda self: self.env.user.employee_id,
    )
    expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="trip_id",
        domain="[('employee_id', '=', employee_id), ('trip_id', '=', False)]",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("request", "Requested"),
            ("receipts", "Collect Receipts"),
            ("done", "Done"),
        ],
        default="draft",
        tracking=True,
    )

    def action_print_trip(self):
        self.ensure_one()
        return self.env.ref("hr_expense_trip.action_report_hr_trip").report_action(self)

    def action_request_approval(self):
        self.ensure_one()
        auto_approve = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hr_expense_trip.auto_approve", default="True")
        )
        if auto_approve == "True":
            self.state = "receipts"
        else:
            self.state = "request"
            manager_employee = self.employee_id.parent_id
            manager = manager_employee.user_id if manager_employee else False
            if manager:
                activity_type = self.env.ref("mail.mail_activity_data_todo")
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=self.env._("Trip Approval Request"),
                    user_id=manager.id,
                )

    def action_approve(self):
        self.ensure_one()
        self.state = "receipts"

    def action_done(self):
        self.ensure_one()
        self.state = "done"
        self._attach_trip_report()

    def _attach_trip_report(self):
        self.ensure_one()
        report = self.env.ref("hr_expense_trip.action_report_hr_trip")
        pdf_content, _mime = report._render_qweb_pdf(self.ids)
        attachment = self.env["ir.attachment"].create(
            {
                "name": self.env._("%s - Trip Report.pdf", self.name),
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
            }
        )
        self.message_post(attachment_ids=[attachment.id])

    @api.constrains("start_date", "end_date")
    def _check_date_range(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    self.env._(
                        "End date (%(end)s) must not be before start date (%(start)s).",
                        end=rec.end_date,
                        start=rec.start_date,
                    )
                )
