# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class AccountMove(models.Model):
    _inherit = "account.move"

    def _payment_state_matters(self):
        self.ensure_one()
        if self.line_ids.expense_id:
            return True
        return super()._payment_state_matters()
