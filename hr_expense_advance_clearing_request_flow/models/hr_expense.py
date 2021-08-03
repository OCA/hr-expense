# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_defaults(self):
        res = super()._prepare_defaults()
        # has_av
        if self.ref_request_id.advance_sheet_id:
            res["advance_sheet_id"] = self.ref_request_id.advance_sheet_id.id
        return res

    @api.onchange("advance_sheet_id")
    def _onchange_advance_sheet_id(self):
        """ onchange for ref_request_id take higher priority """
        if not self.ref_request_id or self.advance_sheet_id:
            super()._onchange_advance_sheet_id()

    # --------------------------------------------
    # Server Actions after AV Action
    # --------------------------------------------

    def approve_expense_sheets(self):
        res = super().approve_expense_sheets()
        for rec in self.filtered(  # Use advance_sheet_ids, to detech AV and not EX
            lambda l: l in l.ref_request_id.advance_sheet_ids
        ):
            rec._run_doc_action("approved", alt_model="hr.advance.sheet")
        return res

    def refuse_sheet(self, reason):
        res = super().refuse_sheet(reason)
        for rec in self.filtered(  # Use advance_sheet_ids, to detech AV and not EX
            lambda l: l in l.ref_request_id.advance_sheet_ids
        ):
            rec._run_doc_action("rejected", alt_model="hr.advance.sheet")
        return res


class HRExpense(models.Model):
    _inherit = "hr.expense"

    @api.depends("product_id", "company_id")
    def _compute_from_product_id_company_id(self):
        super()._compute_from_product_id_company_id()
        # Need advance_amount from context, because default amount was a computed field
        if self.env.context.get("request_advance_amount"):
            advance = self.filtered("advance")
            advance.update({"unit_amount": self.env.context["request_advance_amount"]})
