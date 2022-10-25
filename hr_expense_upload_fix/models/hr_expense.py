# Copyright 2022 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def create_expense_from_attachments(self, attachment_ids=None, view_type="tree"):
        res = super(HrExpense, self).create_expense_from_attachments(
            attachment_ids, view_type
        )
        if res["name"] == "Generated Expense":
            expenses = self.env["hr.expense"].browse(res["res_id"])
        else:
            expenses = self.env["hr.expense"].browse(res["domain"][0][2])
        for expense in expenses:
            expense.product_id = expense.product_id
        return res
