# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    pr_for = fields.Selection(
        selection_add=[("advance", "Advance")],
        ondelete={"advance": "set default"},
    )

    def _do_process_from_purchase_request(self):
        super()._do_process_from_purchase_request()
        sheets = self.filtered(
            lambda l: l.purchase_request_id and l.pr_for == "advance"
        )
        sheets.with_context(advance=True)._create_expenses_from_prlines()

    def _prepare_expense_from_prline(self, line):
        pr_line = super()._prepare_expense_from_prline(line)
        if self.env.context.get("advance"):
            # Change to advance, and product to clearing_product_id
            av_line = self.env["hr.expense"].new({"advance": True})
            av_line.onchange_advance()
            av_line._compute_from_product_id_company_id()
            av_line = av_line._convert_to_write(av_line._cache)
            # Assign known values
            pr_line["clearing_product_id"] = pr_line["product_id"]
            pr_line["product_id"] = av_line["product_id"]
            pr_line["advance"] = av_line["advance"]
            pr_line["name"] = av_line["name"]
            pr_line["account_id"] = av_line["account_id"]
        return pr_line

    @api.onchange("advance_sheet_id")
    def _onchange_advance_sheet_id(self):
        super()._onchange_advance_sheet_id()
        # Advance and PR shouldnot work together
        if self.advance_sheet_id:
            self.purchase_request_id = False
