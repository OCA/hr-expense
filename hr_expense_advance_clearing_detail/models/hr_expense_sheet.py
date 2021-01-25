# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    advance_line = fields.One2many(
        comodel_name="hr.expense.advance.line",
        compute="_compute_advance_line",
        readonly=True,
    )
    clearing_line = fields.One2many(
        comodel_name="hr.expense",
        compute="_compute_clearing_line",
        readonly=True,
    )

    @api.depends("advance", "advance_sheet_id")
    def _compute_advance_line(self):
        for sheet in self:
            sheet.advance_line = False
            if sheet.advance:
                sheet.advance_line = sheet.expense_line_ids.advance_line
            elif sheet.advance_sheet_id:
                sheet.advance_line = (
                    sheet.advance_sheet_id.expense_line_ids.advance_line
                )

    @api.depends("advance", "expense_line_ids")
    def _compute_clearing_line(self):
        for sheet in self:
            sheet.clearing_line = False
            if sheet.advance:
                expense = self.search([("advance_sheet_id", "=", sheet.id)])
                sheet.clearing_line = expense.expense_line_ids

    def _prepare_expense_clearing(self):
        expense_product = self.env.ref("hr_expense.product_product_fixed_cost")
        employee_id = self.expense_line_ids.employee_id
        expense_vals = [
            {
                "name": line.name,
                "product_id": expense_product.id,
                "unit_amount": line.unit_amount,
                "quantity": 1,
                "employee_id": employee_id.id,
            }
            for line in self.advance_line
        ]
        return expense_vals

    def _create_clearing_expense(self):
        self.ensure_one()
        expense_vals = self._prepare_expense_clearing()
        expenses = self.env["hr.expense"].create(expense_vals)
        return expenses

    def open_clear_advance(self):
        vals = super().open_clear_advance()
        self.ensure_one()
        expenses = self._create_clearing_expense()
        vals["context"]["default_expense_line_ids"] = expenses.ids
        return vals
