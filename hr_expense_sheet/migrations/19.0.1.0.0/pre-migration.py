# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import SUPERUSER_ID, api

from odoo.addons.hr_expense_sheet.hooks import pre_init_hook


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    pre_init_hook(env)
