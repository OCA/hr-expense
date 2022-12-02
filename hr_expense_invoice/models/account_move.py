# Copyright 2019 Ecosoft <saranl@ecosoft.co.th>
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2022 ForgeFlow - Jordi Ballester
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_ids = fields.One2many(
        comodel_name="hr.expense", inverse_name="invoice_id", string="Expenses"
    )
    expense_count = fields.Integer(compute="_compute_expense_count")

    @api.constrains("amount_total")
    def _check_expense_ids(self):
        for move in self.filtered("expense_ids"):
            DecimalPrecision = self.env["decimal.precision"]
            precision = DecimalPrecision.precision_get("Product Price")
            expense_amount = sum(move.expense_ids.mapped("total_amount"))
            if float_compare(expense_amount, move.amount_total, precision) != 0:
                raise ValidationError(
                    _(
                        "You can't change the total amount, as there's an expense "
                        "linked to this invoice."
                    )
                )

    def _compute_expense_count(self):
        for rec in self:
            rec.expense_count = len(rec.expense_ids)

    def action_view_expenses(self):
        self.ensure_one()
        action = self.env.ref("hr_expense.hr_expense_actions_my_all")
        result = action.sudo().read()[0]
        res = self.env.ref("hr_expense.hr_expense_view_form", False)
        expenses = self.expense_ids
        result["context"] = {}
        if len(expenses) != 1:
            result["domain"] = "[('id', 'in', " + str(expenses.ids) + ")]"
        elif len(expenses) == 1:
            result["views"] = [(res and res.id or False, "form")]
            result["res_id"] = expenses.ids[0]
        return result
