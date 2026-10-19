# Copyright 2026 KMEE
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    """amount_residual is now computed from the transfer entries of the expenses paid by
    the employee with a vendor bill: recompute it for the existing sheets."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    sheets = env["hr.expense.sheet"].search(
        [("expense_line_ids.invoice_id", "!=", False)]
    )
    env.add_to_compute(sheets._fields["amount_residual"], sheets)
    env.flush_all()
