# Copyright 2021 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _auto_update_field_company(cr, env):
    _logger.info(
        "Add value 'payment_cancel_policy', 'je_cancel_policy' and 'ex_cancel_policy' to "
        "company on upgrade to 15.0.1.2.0"
    )
    env.cr.execute(
        "ALTER TABLE res_company ADD x varchar,ADD x2 varchar,ADD x3 varchar;"
    )
    # add default
    env.cr.execute("UPDATE res_company SET x='cancel',x2='cancel',x3='draft';")


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _auto_update_field_company(cr, env)
