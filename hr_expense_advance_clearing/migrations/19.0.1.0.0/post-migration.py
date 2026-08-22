# Copyright 2024 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

from openupgradelib import openupgrade

_logger = logging.getLogger(__name__)


@openupgrade.migrate()
def migrate(env, version):
    """Move the surviving 18.0 line-level advance/clearing data onto the 19.0
    per-expense fields (expense_type and clearing_advance_id)."""
    cr = env.cr

    # 1) expense_type from the 18.0 line-level `advance` boolean. The old
    #    column lingers on hr_expense until ORM cleanup, so it is readable here.
    if openupgrade.column_exists(cr, "hr_expense", "advance"):
        openupgrade.logged_query(
            cr,
            """
            UPDATE hr_expense
            SET expense_type = CASE WHEN advance THEN 'advance' ELSE 'expense' END
            WHERE expense_type IS NULL
            """,
        )
    # expense_type is required; default any remaining rows to 'expense'.
    openupgrade.logged_query(
        cr,
        "UPDATE hr_expense SET expense_type = 'expense' WHERE expense_type IS NULL",
    )

    # 2) clearing_advance_id from the 18.0 line-level `av_line_id`: it linked a
    #    clearing expense to the advance expense it cleared — the exact
    #    semantics of the new per-expense clearing_advance_id.
    if openupgrade.column_exists(cr, "hr_expense", "av_line_id"):
        openupgrade.logged_query(
            cr,
            """
            UPDATE hr_expense clr
            SET clearing_advance_id = adv.id
            FROM hr_expense adv
            WHERE clr.av_line_id = adv.id
              AND adv.expense_type = 'advance'
              AND clr.clearing_advance_id IS NULL
            """,
        )

    # 3) Sheet-level links the line-level pass could not reconstruct are NOT
    #    auto-linked (a clearing report grouped many expenses against one
    #    advance; blindly linking every line would over-attribute the draw-down
    #    and corrupt the residual). Instead, report them for manual review.
    if openupgrade.table_exists(cr, "_ou_haac_sheet_link"):
        cr.execute(
            """
            SELECT DISTINCT clr.id
            FROM hr_expense clr
            JOIN _ou_haac_sheet_link link ON clr.former_sheet_id = link.sheet_id
            WHERE clr.clearing_advance_id IS NULL
              AND clr.expense_type = 'expense'
            """
        )
        unresolved = [r[0] for r in cr.fetchall()]
        if unresolved:
            _logger.warning(
                "hr_expense_advance_clearing: %d expense(s) belonged to a "
                "clearing report (sheet-level advance_sheet_id) but had no "
                "line-level av_line_id; clearing_advance_id left empty for "
                "manual review: %s",
                len(unresolved),
                unresolved,
            )
        openupgrade.logged_query(cr, "DROP TABLE _ou_haac_sheet_link")

    _logger.info("hr_expense_advance_clearing: advance/clearing data migrated.")
