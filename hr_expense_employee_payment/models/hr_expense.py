# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    conciliation_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Conciliation Entry",
        compute="_compute_conciliation_move_id",
        store=True,
        help="Intermediate entry created to reconcile with the vendor "
        "bill and payment later.",
    )

    @api.depends("sheet_id.account_move_ids.move_type")
    def _compute_conciliation_move_id(self):
        for expense in self:
            if not expense.sheet_id.account_move_ids:
                continue
            expense_conciliation_moves = expense.sheet_id._get_conciliation_moves(
                posted=False
            )
            expense.conciliation_move_id = expense_conciliation_moves[:1]
