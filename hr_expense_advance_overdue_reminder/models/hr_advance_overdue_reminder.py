# Copyright 2020 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo import _, api, fields, models, tools
from odoo.exceptions import UserError


class HrAdvanceOverdueReminder(models.Model):
    _name = "hr.advance.overdue.reminder"
    _inherit = "overdue.reminder.abstract"
    _description = "Hr Advance Overdue Reminder"

    expense_sheet_ids = fields.Many2many(
        comodel_name="hr.expense.sheet",
        relation="expense_sheet_overdue_reminder_rel",
        column1="overdue_reminder_id",
        column2="expense_sheet_id",
        string="Overdue Expense Advance Sheet",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def action_get_mail_view(self):
        action_ref = self.env.ref("mail.action_view_mail_mail")
        action = action_ref.read()[0]
        action["domain"] = self._domain_search_mail()
        return action

    def total_residual(self):
        self.ensure_one()
        res = {}
        for exp in self.expense_sheet_ids:
            if exp.currency_id in res:
                res[exp.currency_id] += exp.residual
            else:
                res[exp.currency_id] = exp.residual
        return res.items()

    @api.model
    def _hook_mail_template(self, action, vals, mail_subject=False, mail_body=False):
        mail_subject, mail_body = super()._hook_mail_template(
            action, mail_subject, mail_body
        )
        MailTemplate = self.env["mail.template"]
        model = self._context.get("active_model", False)
        if model == "hr.expense.sheet" and vals["reminder_type"] == "mail":
            commercial_partner = self.env["res.partner"].browse(
                vals["commercial_partner_id"]
            )
            mail_tpl = MailTemplate.browse(vals["mail_template_id"])
            mail_tpl_lang = mail_tpl.with_context(
                lang=commercial_partner.lang or "en_US"
            )
            mail_subject = mail_tpl_lang._render_template(
                mail_tpl_lang.subject, self._name, action.id
            )
            mail_body = mail_tpl_lang._render_template(
                mail_tpl_lang.body_html, self._name, action.id
            )
            if mail_tpl.user_signature:
                signature = self.env.user.signature
                if signature:
                    mail_body = tools.append_content_to_html(
                        mail_body, signature, plaintext=False
                    )
            mail_body = tools.html_sanitize(mail_body)
        return mail_subject, mail_body

    def _get_report_base_filename(self):
        self.ensure_one()
        fname = "overdue_letter-%s" % self.commercial_partner_id.name.replace(" ", "_")
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

    def _prepare_attach_letter(self, mail):
        attachment_ids = []
        IrAttachment = self.env["ir.attachment"]
        for exp in self.expense_sheet_ids:
            if self.letter_report.report_type in ("qweb-html", "qweb-pdf"):
                report_bin, report_format = self.letter_report.render_qweb_pdf([exp.id])
            else:
                res = self.letter_report and self.letter_report.render([exp.id])
                if not res:
                    raise UserError(
                        _("Report format '%s' is not supported.")
                        % self.letter_report.report_type
                    )
                report_bin, report_format = res
            # WARN : update when backporting
            filename = "{}.{}".format(self._get_report_base_filename(), report_format)
            attach = IrAttachment.create(
                {
                    "name": filename,
                    "datas": base64.b64encode(report_bin),
                    "res_model": "mail.message",
                    "res_id": mail.mail_message_id.id,
                }
            )
            attachment_ids.append(attach.id)
        return attachment_ids

    def validate_mail(self):
        self.ensure_one()
        if not self.partner_id.email:
            raise UserError(
                _("E-mail missing on partner '%s'.") % self.partner_id.display_name
            )
        if not self.mail_subject:
            raise UserError(_("Mail subject is empty."))
        if not self.mail_body:
            raise UserError(_("Mail body is empty."))
        xmlid = (
            "hr_expense_advance_overdue_reminder"
            ".hr_advance_overdue_reminder_mail_template"
        )
        mvals = self.env.ref(xmlid).generate_email(self.id)
        mvals.update({"subject": self.mail_subject, "body_html": self.mail_body})
        mvals.pop("attachment_ids", None)
        mvals.pop("attachments", None)
        mail = self.env["mail.mail"].create(mvals)
        if self.attachment_letter:
            attachment_ids = self._prepare_attach_letter(mail)
            mail.write({"attachment_ids": [(6, 0, attachment_ids)]})
        return mail

    def _create_sequence(self):
        self.ensure_one()
        Sequence = self.env["ir.sequence"]
        sequence_code = "advance.overdue.reminder.sequence"
        if self.name == "/":
            self.name = Sequence.with_context(ir_sequence_date=self.date).next_by_code(
                sequence_code
            )
        return True

    def action_validate(self):
        MailActivity = self.env["mail.activity"]
        action = True
        for rec in self:
            if rec.reminder_type == "mail":
                rec.validate_mail()
            elif rec.reminder_type == "letter":
                action = rec.print_letter()
            if rec.create_activity:
                MailActivity.create(self._prepare_mail_activity())
            rec._create_sequence()
        self.write({"state": "done"})
        return action

    def action_cancel(self):
        return self.write({"state": "cancel"})
