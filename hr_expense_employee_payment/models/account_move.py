# Copyright 2026 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import models
from odoo.fields import Domain


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_force_register_payment(self):
        # Check if there are any Expense Vendor Moves in order to modify normal workflow
        expense_vendor_moves_domain = Domain.AND(
            [
                Domain("expense_ids", "!=", False),
                self.env["hr.expense"]._get_vendor_moves_domain(),
            ]
        )
        expense_moves = self.filtered_domain(expense_vendor_moves_domain)
        if not expense_moves:
            return super().action_force_register_payment()

        # Other Payable lines
        other_moves = self - expense_moves
        payable_lines = other_moves.line_ids
        # Payable Employee Expense lines
        expense_moves.expense_ids._create_conciliation_moves(auto_reconcile=True)
        payable_lines |= expense_moves.expense_ids._get_conciliation_payable_move_lines(
            for_employee=True
        )
        return payable_lines.action_register_payment()
