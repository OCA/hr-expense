# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo.tools.sql import column_exists, table_exists


def _restore_sheets_dropped_by_odoo19(env):
    """Recreate reports removed by the official Odoo 19 upgrade.

    That upgrade drops ``hr_expense_sheet`` and keeps the old id on
    ``hr_expense.former_sheet_id``. Rows must exist before the module init
    adds the foreign key on ``hr_expense.sheet_id``.
    """
    env.cr.execute(
        """
        CREATE TABLE hr_expense_sheet (
            id serial NOT NULL PRIMARY KEY,
            name varchar NOT NULL,
            company_id integer NOT NULL,
            employee_id integer NOT NULL,
            state varchar NOT NULL
        )
        """
    )
    env.cr.execute(
        """
        WITH lines AS (
            SELECT
                former_sheet_id,
                company_id,
                employee_id,
                name,
                id,
                CASE state
                    WHEN 'submit' THEN 'submitted'
                    WHEN 'approve' THEN 'approved'
                    WHEN 'post' THEN 'posted'
                    WHEN 'done' THEN 'paid'
                    WHEN 'cancel' THEN 'refused'
                    ELSE state
                END AS state
            FROM hr_expense
            WHERE former_sheet_id IS NOT NULL
                AND company_id IS NOT NULL
                AND employee_id IS NOT NULL
        )
        INSERT INTO hr_expense_sheet (id, name, company_id, employee_id, state)
        SELECT
            former_sheet_id,
            COALESCE(
                (
                    array_agg(name ORDER BY id)
                    FILTER (WHERE name IS NOT NULL AND name <> '')
                )[1],
                'Expense Report'
            ),
            (array_agg(company_id ORDER BY id))[1],
            (array_agg(employee_id ORDER BY id))[1],
            CASE
                WHEN bool_and(state = 'draft') THEN 'draft'
                WHEN bool_and(state = 'submitted') THEN 'submitted'
                WHEN bool_and(state = 'approved') THEN 'approved'
                WHEN bool_and(state = 'posted') THEN 'posted'
                WHEN bool_or(state = 'in_payment') THEN 'in_payment'
                WHEN bool_and(state = 'paid') THEN 'paid'
                WHEN bool_and(state IN ('posted', 'paid')) THEN 'posted'
                WHEN bool_and(state = 'refused') THEN 'refused'
                ELSE 'draft'
            END
        FROM lines
        GROUP BY former_sheet_id
        """
    )
    env.cr.execute("SELECT MAX(id) FROM hr_expense_sheet")
    max_id = env.cr.fetchone()[0]
    if max_id:
        env.cr.execute(
            "SELECT setval(pg_get_serial_sequence('hr_expense_sheet', 'id'), %s)",
            (max_id,),
        )


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
    # Official Odoo 19 upgrades drop the sheet table. Rebuild it before the
    # foreign key on hr_expense.sheet_id is created.
    if not table_exists(env.cr, "hr_expense_sheet"):
        _restore_sheets_dropped_by_odoo19(env)
        if not column_exists(env.cr, "hr_expense", "sheet_id"):
            env.cr.execute(
                "ALTER TABLE hr_expense ADD COLUMN IF NOT EXISTS sheet_id integer"
            )
        env.cr.execute(
            """
            UPDATE hr_expense AS expense
            SET sheet_id = expense.former_sheet_id
            WHERE expense.former_sheet_id IS NOT NULL
                AND EXISTS (
                    SELECT 1
                    FROM hr_expense_sheet AS sheet
                    WHERE sheet.id = expense.former_sheet_id
                )
            """
        )
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
