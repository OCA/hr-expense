# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import SUPERUSER_ID, api


def post_init_hook(cr, registry):
    """Trying to fill the source expense sheet in payments"""
    env = api.Environment(cr, SUPERUSER_ID, {})
    sheets = env["hr.expense.sheet"].search([("payment_mode", "=", "own_account")])
    for sheet in sheets:
        amls = sheet.account_move_id.mapped("line_ids")
        reconcile = amls.mapped("full_reconcile_id")
        aml_payment = reconcile.mapped("reconciled_line_ids").filtered(
            lambda r: r not in amls
        )
        payment = aml_payment.mapped("payment_id")
        payment.write({"expense_sheet_ids": sheet.ids})
