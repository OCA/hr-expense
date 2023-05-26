# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    def _action_send_mail(self, **kwargs):
        for wizard in self:
            if wizard.model == "hr.advance.overdue.reminder":
                overdue = self.env[wizard.model].sudo().browse(wizard.res_id)
                overdue._update_overdue_advance()
        return super()._action_send_mail(**kwargs)
