# Copyright 2019 Kitti U. <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def reconcile(self, writeoff_acc_id=False, writeoff_journal_id=False):
        if self._context.get("use_hr_expense_invoice"):
            obj = self.filtered(lambda l: not l.reconciled)
        obj = self
        return super(AccountMoveLine, obj).reconcile(
            writeoff_acc_id=writeoff_acc_id, writeoff_journal_id=writeoff_journal_id
        )
