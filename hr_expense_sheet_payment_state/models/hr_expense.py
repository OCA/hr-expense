# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.account.models.account_move import PAYMENT_STATE_SELECTION


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    payment_state = fields.Selection(selection=PAYMENT_STATE_SELECTION, string="Payment Status",
        store=True, readonly=True, copy=False, tracking=True, compute='_compute_payment_state')

    @api.depends("account_move_id.payment_state")
    def _compute_payment_state(self):
        for sheet in self:
            sheet.payment_state = sheet.account_move_id.payment_state or "not_paid"
