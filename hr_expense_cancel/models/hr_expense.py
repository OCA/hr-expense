# Copyright 2019 Tecnativa - Ernesto Tejeda
# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_cancel(self):
        move_cancel_state = self.env.company.expense_move_cancel
        for sheet in self:
            sheet.account_move_id.button_cancel()
        if move_cancel_state != "cancel":
            self.mapped("expense_line_ids").write({"is_refused": False})
        return self.write({"state": move_cancel_state})


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def refuse_expense(self, reason):
        payment_cancel_state = self.env.company.expense_payment_cancel
        if (
            self.env.context.get("expense_sheet_ids")
            and payment_cancel_state != "cancel"
        ):
            return self.sheet_id.write({"state": payment_cancel_state})
        return super().refuse_expense(reason)
