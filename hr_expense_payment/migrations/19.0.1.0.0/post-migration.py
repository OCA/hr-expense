# Copyright 2026 Don Kendall
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo.tools.sql import table_exists

_logger = logging.getLogger(__name__)

LEGACY_RELATION = "payment_expense_sheet_rel"


def migrate(cr, version):
    """Carry 18.0 rel rows whose reconciliation was since undone into core's
    account_move__account_payment, via hr.expense.former_sheet_id (the legacy
    pointer upgrade tools fill). Wizard-recorded links already live there and
    survive on their own. Idempotent; no-op when the table is absent or the
    pointer was left unfilled.
    """
    if not table_exists(cr, LEGACY_RELATION):
        return
    cr.execute("SELECT COUNT(*) FROM hr_expense WHERE former_sheet_id IS NOT NULL")
    if not cr.fetchone()[0]:
        _logger.warning(
            "%s exists but hr_expense.former_sheet_id is unfilled; the "
            "upgrade path kept no sheet mapping, no links carried.",
            LEGACY_RELATION,
        )
        return
    cr.execute(
        """
        INSERT INTO account_move__account_payment (invoice_id, payment_id)
        SELECT DISTINCT expense.account_move_id, legacy.payment_id
        FROM payment_expense_sheet_rel AS legacy
        JOIN hr_expense AS expense ON expense.former_sheet_id = legacy.sheet_id
        WHERE expense.account_move_id IS NOT NULL
          AND EXISTS (
              SELECT 1 FROM account_payment AS payment
              WHERE payment.id = legacy.payment_id
          )
          AND NOT EXISTS (
              SELECT 1 FROM account_move__account_payment AS existing
              WHERE existing.invoice_id = expense.account_move_id
                AND existing.payment_id = legacy.payment_id
          )
        """
    )
    _logger.info(
        "hr_expense_payment: carried %s payment link(s) from %s onto the "
        "expense journal entries.",
        cr.rowcount,
        LEGACY_RELATION,
    )
