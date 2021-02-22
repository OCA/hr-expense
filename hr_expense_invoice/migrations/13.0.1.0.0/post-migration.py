# Copyright 2021 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from openupgradelib import openupgrade
from psycopg2 import sql


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        sql.SQL(
            "UPDATE hr_expense he SET invoice_id = am.id "
            "FROM account_move am WHERE am.old_invoice_id = he.{}"
        ).format(sql.Identifier(openupgrade.get_legacy_name("invoice_id"))),
    )
