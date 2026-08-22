# Copyright 2024 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """Stash the sheet-level advance link before core drops hr.expense.sheet,
    so post-migration can flag any clearing the line-level pass misses."""
    cr = env.cr
    if not openupgrade.table_exists(
        cr, "hr_expense_sheet"
    ) or not openupgrade.column_exists(cr, "hr_expense_sheet", "advance_sheet_id"):
        _logger.info(
            "hr_expense_advance_clearing: hr.expense.sheet already removed; "
            "clearing links will be rebuilt from hr_expense.av_line_id."
        )
        return
    openupgrade.logged_query(
        cr,
        """
        CREATE TABLE IF NOT EXISTS _ou_haac_sheet_link AS
            SELECT id AS sheet_id, advance_sheet_id
            FROM hr_expense_sheet
            WHERE advance_sheet_id IS NOT NULL
        """,
    )
