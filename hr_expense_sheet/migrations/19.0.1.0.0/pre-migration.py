# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo.addons.hr_expense_sheet.hooks import pre_init_hook


def migrate(env, version):
    pre_init_hook(env)
