# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tools.sql import column_exists


def pre_init_hook(env):
    """We renamed fields and field values to align with those in hr.expense."""
    env.cr.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM hr_expense
            WHERE former_sheet_id IS NOT NULL
        )
    """)
    has_former_sheet = env.cr.fetchone()[0]
    if not has_former_sheet:
        return
    # Create sheet_id column + fill (related to https://github.com/OCA/OpenUpgrade/blob/c402d59cd518dadbabd7d6410d488ee3e81e795c/openupgrade_scripts/scripts/hr_expense/19.0.2.1/pre-migration.py#L12)
    if not column_exists(env.cr, "hr_expense", "sheet_id"):
        env.cr.execute(
            "ALTER TABLE hr_expense ADD COLUMN IF NOT EXISTS sheet_id integer"
        )
        env.cr.execute(
            """
            UPDATE hr_expense
            SET sheet_id = former_sheet_id
            WHERE former_sheet_id IS NOT NULL
            """
        )
    # Change states
    env.cr.execute(
        "UPDATE hr_expense_sheet SET state = 'submitted' WHERE state = 'submit'"
    )
    env.cr.execute(
        "UPDATE hr_expense_sheet SET state = 'approved' WHERE state = 'approve'"
    )
    if column_exists(env.cr, "hr_expense_sheet", "payment_state"):
        env.cr.execute(
            """
            UPDATE hr_expense_sheet
            SET state = 'posted'
            WHERE state = 'post' AND payment_state = 'not_paid'
            """
        )
        env.cr.execute(
            """
            UPDATE hr_expense_sheet
            SET state = 'in_payment'
            WHERE state = 'post' AND payment_state = 'partial'
            """
        )
        env.cr.execute(
            """
            UPDATE hr_expense_sheet
            SET state = 'paid'
            WHERE (
                state = 'post' AND payment_state IN ('paid', 'reversed')
            ) OR state = 'done'
            """
        )
    env.cr.execute(
        "UPDATE hr_expense_sheet SET state = 'refused' WHERE state = 'cancel'"
    )
    # Change approval_state
    env.cr.execute(
        """
        UPDATE hr_expense_sheet
        SET approval_state = 'submitted'
        WHERE approval_state = 'submit'
        """
    )
    env.cr.execute(
        """
        UPDATE hr_expense_sheet
        SET approval_state = 'approved'
        WHERE approval_state = 'approve'
        """
    )
    env.cr.execute(
        """
        UPDATE hr_expense_sheet
        SET approval_state = 'posted'
        WHERE approval_state = 'post'"""
    )
    env.cr.execute(
        """
        UPDATE hr_expense_sheet
        SET approval_state = 'refused'
        WHERE approval_state = 'cancel'
        """
    )
    # Rename fields
    if column_exists(env.cr, "hr_expense_sheet", "user_id"):
        env.cr.execute(
            """
            ALTER TABLE hr_expense_sheet
            RENAME COLUMN user_id TO manager_id
            """
        )
    if column_exists(env.cr, "hr_expense_sheet", "total_tax_amount"):
        env.cr.execute(
            """
            ALTER TABLE hr_expense_sheet
            RENAME COLUMN total_tax_amount TO tax_amount
            """
        )
