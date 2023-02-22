# Copyright 2023 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def action_unpost(self):
        """Update state expense to your config when cancel expense"""
        res = super().action_unpost()
        ex_cancel_policy = self.env.company.ex_cancel_policy
        if ex_cancel_policy != "draft":
            self.write({"state": ex_cancel_policy})
        return res


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def refuse_expense(self, reason):
        """Skip refuse expense if send context 'skip_refuse_expense'
        for case cancel JE with backward state"""
        if self._context.get("skip_refuse_expense", False):
            return
        return super().refuse_expense(reason)
