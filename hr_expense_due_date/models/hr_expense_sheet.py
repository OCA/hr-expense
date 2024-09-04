# Copyright 2024 - TODAY, Kaynnan Lemes <kaynnan.lemes@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HrExpenseSheet(models.Model):

    _inherit = "hr.expense.sheet"

    payment_term_id = fields.Many2one(
        "account.payment.term",
        company_dependent=True,
        string="Payment Terms",
        domain="[('company_id', 'in', [current_company_id, False])]",
    )
    due_date = fields.Date(string="Due Date")
