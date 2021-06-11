# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    advance_line = fields.One2many(
        string="Advance Detail",
        comodel_name="hr.expense.advance.line",
        inverse_name="sheet_id",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def action_submit_sheet(self):
        self._check_advance_detail_amount()
        return super().action_submit_sheet()

    def _check_advance_detail_amount(self):
        for sheet in self.filtered("advance"):
            if not sheet.advance_line:
                continue
            advance_detail_amount = sum(sheet.advance_line.mapped("unit_amount"))
            if sheet.total_amount != advance_detail_amount:
                format_amount = self.env["digest.digest"]._format_currency_amount(
                    sheet.total_amount, sheet.currency_id
                )
                raise UserError(
                    _("Advance detial amount must equal advnance amount %s")
                    % format_amount
                )

    @api.onchange("advance_sheet_id")
    def _onchange_advance_sheet_id(self):
        AdvanceLine = self.env["hr.expense.advance.line"]
        self.advance_line = False
        self.advance_sheet_id.advance_line.read()  # prefetch
        for line in self.advance_sheet_id.advance_line:
            avline = line._convert_to_write(line._cache)
            avline["av_line_id"] = self.advance_sheet_id.expense_line_ids[:1]
            self.advance_line += AdvanceLine.new(avline)

    @api.model
    def create(self, vals):
        sheet = super().create(vals)
        if "advance_sheet_id" in vals:
            sheet.mapped("expense_line_ids").filtered("av_line_id").unlink()
        sheet._create_expenses_from_avlines()
        sheet.advance_line.filtered("av_line_id").unlink()
        return sheet

    def write(self, vals):
        res = super().write(vals)
        if "advance_sheet_id" in vals:
            self.mapped("expense_line_ids").filtered("av_line_id").unlink()
        self._create_expenses_from_avlines()
        self.mapped("advance_line").filtered("av_line_id").unlink()
        return res

    def _create_expenses_from_avlines(self):
        for sheet in self.filtered("advance_sheet_id"):
            expenses_list = []
            for avline in sheet.advance_line:
                # First get all columns values form the original advance
                expense_dict = self.env["hr.expense"]._convert_to_write(
                    avline.av_line_id.read()[0]
                )
                # Remove unused fields, i.e., mail.thread and mail.activity.mixin
                magic_fields = list(self.env["mail.thread"]._fields.keys())
                magic_fields += list(self.env["mail.activity.mixin"]._fields.keys())
                magic_fields = list(set(magic_fields))
                expense_dict = {
                    k: v for k, v in expense_dict.items() if k not in magic_fields
                }
                # Set value we know require changing
                expense_product = self.env.ref("hr_expense.product_product_fixed_cost")
                expense_dict.update(
                    {
                        "date": fields.Date.context_today(self),
                        "advance": False,
                        "product_id": expense_product.id,
                        "quantity": 1,
                    }
                )
                # As object, call compute function
                expense = self.env["hr.expense"].new(expense_dict)
                expense._compute_from_product_id_company_id()
                expense_dict = expense._convert_to_write(expense._cache)
                # Finally, update with desired values from advance_line
                sheet_av_line = self.env["hr.expense"]._convert_to_write(
                    avline.read()[0]
                )
                expense_dict.update(sheet_av_line)
                # Add creation list
                expenses_list.append(expense_dict)
            self.env["hr.expense"].sudo().create(expenses_list)
