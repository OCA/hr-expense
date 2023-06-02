# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2020 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        expense_sheet_ids = self._context.get("expense_sheet_ids", False)
        # for case expense not group payments only
        if expense_sheet_ids and len(expense_sheet_ids) == 1:
            sheet_id = int("".join([str(sheet_id) for sheet_id in expense_sheet_ids]))
            payment_vals.update(expense_sheet_id=sheet_id)
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        expense_sheet_ids = self._context.get("expense_sheet_ids", False)
        if expense_sheet_ids:
            move_line_ids = self.env["account.move.line"].browse(
                batch_result["lines"].ids
            )
            sheet_ids = self.env["hr.expense.sheet"].browse(expense_sheet_ids)
            sheet_id = sheet_ids.filtered(
                lambda l: l.account_move_id.id == move_line_ids.move_id.id
            )
            payment_vals.update(expense_sheet_id=sheet_id.id)
        return payment_vals
