# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models

PAYMENT_STATE_SELECTION = [
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
]


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_state = fields.Selection(PAYMENT_STATE_SELECTION, string="Payment Status", store=True,
        readonly=True, copy=False, tracking=True, compute='_compute_amount')

    def _payment_state_matters(self):
        ''' Determines when new_pmt_state must be upated.
        Method created to allow overrides.
        :return: Boolean '''
        self.ensure_one()
        return self.is_invoice(include_receipts=True)
