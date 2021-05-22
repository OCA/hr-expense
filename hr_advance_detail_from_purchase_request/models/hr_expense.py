# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    pr_for = fields.Selection(
        selection_add=[("advance", "Advance")],
        ondelete={"advance": "set default"},
    )

    def _do_process_from_purchase_request(self):
        super()._do_process_from_purchase_request()
        sheets = self.filtered(lambda l: l.pr_for == "advance")
        sheets._create_advance_detail_from_prlines()

    def _create_advance_detail_from_prlines(self):
        """1. create an advance expense line
        2. create advance detail from prline"""
        Expense = self.env["hr.expense"]
        for sheet in self.filtered("purchase_request_id"):
            advance = Expense.new({"advance": True})
            advance.onchange_advance()
            advance_dict = advance._convert_to_write(advance._cache)
            advance_dict = sheet._prepare_advance_dict(advance_dict)
            # 1. create an advance expense line
            advance = Expense.create(advance_dict)
            advance_lines = []
            # 2. create advance detail from prline
            for pr_line in sheet.pr_line_ids:
                advance_line = self._prepare_advance_line_dict(advance, pr_line)
                advance_lines.append(advance_line)
            self.env["hr.expense.advance.line"].create(advance_lines)

    def _prepare_advance_dict(self, advance_dict):
        self.ensure_one()
        pr = self.purchase_request_id
        advance_dict.update(
            {
                "name": pr.description or _("Employee Advance"),
                "employee_id": pr.requested_by.employee_id.id,
                "unit_amount": sum(self.pr_line_ids.mapped("total_amount")),
                "sheet_id": self.id,
            }
        )
        return advance_dict

    def _prepare_advance_line_dict(self, advance, pr_line):
        self.ensure_one()
        # Find valid fields of model hr.expense.advance.line
        advl_fields = list(self.env["hr.expense.advance.line"]._fields.keys())
        # Prepare advance_line dict
        advance_line = pr_line._convert_to_write(pr_line._cache)
        advance_line["expense_id"] = advance.id
        advance_line["unit_amount"] = pr_line.total_amount
        # Make sure only advl_fields is used, to create the advance line.
        advance_line = {k: v for k, v in advance_line.items() if k in advl_fields}
        return advance_line
