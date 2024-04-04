# Copyright 2019 Tecnativa - Ernesto Tejeda
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


def post_init_hook(env):
    """Trying to fill the source expense sheet in payments"""
    sheets = env["hr.expense.sheet"].search([("payment_mode", "=", "own_account")])
    for sheet in sheets:
        amls = sheet.account_move_ids.mapped("line_ids")
        reconcile = amls.mapped("full_reconcile_id")
        aml_payment = reconcile.mapped("reconciled_line_ids").filtered(
            lambda r, amls=amls: r not in amls
        )
        payment = aml_payment.mapped("payment_id")
        payment.write({"expense_sheet_ids": sheet.ids})
