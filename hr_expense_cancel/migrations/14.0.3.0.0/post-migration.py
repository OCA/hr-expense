# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _auto_update_field_company(cr, env):
    _logger.info(
        "Add value 'expense_cancel_policy' and 'expense_cancel_state' to "
        "company on upgrade to 14.0.3.0.0"
    )
    companys = env["res.company"].search([])
    for company in companys:
        if not company.expense_cancel_policy:
            env.cr.execute(
                "ALTER TABLE res_company ADD COLUMN expense_cancel_policy "
                "char WHERE id={};".format(company.id)
            )
        if not company.expense_cancel_state:
            env.cr.execute(
                "ALTER TABLE res_company ADD COLUMN expense_cancel_state "
                "char WHERE id={};".format(company.id)
            )
    # add default
    env.cr.execute("UPDATE res_company SET expense_cancel_policy = 'unlink';")
    env.cr.execute("UPDATE res_company SET expense_cancel_state = 'submit';")


def migrate(cr, version):
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        _auto_update_field_company(cr, env)
