from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE hr_expense expense
           SET account_move_id = move.id
          FROM account_move move
         WHERE move.source_invoice_expense_id = expense.id
           AND expense.account_move_id IS NULL
        """,
    )
