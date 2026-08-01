# Copyright 2026 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.tools.sql import SQL


class PettyCashTransaction(models.Model):
    _name = "petty.cash.transaction"
    _description = "Petty Cash Transaction"
    _auto = False
    _order = "id desc"

    _depends = {
        "account.move.line": [
            "date",
            "debit",
            "credit",
            "partner_id",
            "account_id",
            "move_id",
            "company_id",
            "parent_state",
            "expense_id",
        ],
        "account.move": ["name", "is_petty_cash", "expense_sheet_id"],
        "petty.cash": ["partner_id", "account_id", "company_id"],
    }

    date = fields.Date()
    name = fields.Char()
    petty_cash_id = fields.Many2one(
        comodel_name="petty.cash",
        string="Petty Cash Holder",
    )
    move_id = fields.Many2one(
        comodel_name="account.move",
        string="Document",
    )
    sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        string="Expense Report",
    )
    expense_id = fields.Many2one(
        comodel_name="hr.expense",
    )
    partner_id = fields.Many2one(comodel_name="res.partner")
    account_id = fields.Many2one(comodel_name="account.account")
    source = fields.Selection(
        selection=[
            ("refill", "Refill"),
            ("expense", "Expense"),
        ],
    )
    debit = fields.Float()
    credit = fields.Float()
    amount = fields.Float()
    balance = fields.Float()
    company_id = fields.Many2one(comodel_name="res.company")

    @property
    def _table_query(self) -> SQL:
        return SQL("%s %s %s", self._select(), self._from(), self._where())

    @api.model
    def _select(self) -> SQL:
        return SQL(
            """
            SELECT
                aml.id AS id,
                aml.date AS date,
                am.name AS name,
                pc.id AS petty_cash_id,
                aml.move_id AS move_id,
                am.expense_sheet_id AS sheet_id,
                aml.expense_id AS expense_id,
                aml.partner_id AS partner_id,
                aml.account_id AS account_id,
                CASE
                    WHEN am.is_petty_cash THEN 'refill'
                    WHEN am.expense_sheet_id IS NOT NULL THEN 'expense'
                END AS source,
                aml.debit AS debit,
                aml.credit AS credit,
                (aml.debit - aml.credit) AS amount,
                SUM(aml.debit - aml.credit) OVER (
                    PARTITION BY pc.id
                    ORDER BY aml.date, aml.id
                ) AS balance,
                aml.company_id AS company_id
            """
        )

    @api.model
    def _from(self) -> SQL:
        return SQL(
            """
            FROM account_move_line aml
            JOIN account_move am ON am.id = aml.move_id
            JOIN petty_cash pc
                ON pc.partner_id = aml.partner_id
                AND pc.account_id = aml.account_id
                AND pc.company_id = aml.company_id
            """
        )

    @api.model
    def _where(self) -> SQL:
        return SQL("WHERE aml.parent_state = 'posted'")
