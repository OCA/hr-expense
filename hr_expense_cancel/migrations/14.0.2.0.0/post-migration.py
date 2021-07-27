# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _auto_update_field_expense_sheet_ids(cr, env):
    _logger.info(
        "Add value 'expense_sheet_id' to 'expense_sheet_ids' on upgrade to 14.0.2.0.0"
    )
    payment_obj = env["account.payment"]
    expense_sheet_obj = env["hr.expense.sheet"]
    cr.execute(
        "SELECT id, expense_sheet_id FROM account_payment WHERE expense_sheet_id is not null"
    )
    payments = cr.dictfetchall()
    for payment in payments:
        expense_sheet_id = expense_sheet_obj.browse(payment["expense_sheet_id"])
        payment_id = payment_obj.search([("id", "=", payment["id"])])
        payment_id.write({"expense_sheet_ids": [(6, 0, expense_sheet_id.ids)]})
    _logger.info("Drop column 'expense_sheet_id' on upgrade to 14.0.2.0.0")
    env.cr.execute("ALTER TABLE account_payment DROP COLUMN expense_sheet_id")


def migrate(cr, version):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        _auto_update_field_expense_sheet_ids(cr, env)
