# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class HRExpenseSheet(models.Model):
    _name = "hr.expense.sheet"
    _inherit = ["hr.expense.sheet", "request.doc.mixin"]
    _request_freeze_states = ["pending"]
    _doc_approved_states = ["approve"]

    # --------------------------------------------
    # Default values pass to EX
    # --------------------------------------------

    def _prepare_defaults(self):
        res = super()._prepare_defaults()
        request = self.ref_request_id
        lines = []
        for line in request.product_line_ids:
            vals = {
                "product_id": line.product_id.id,
                "name": line.description,
                "quantity": line.quantity,
                "unit_amount": line.price_unit,
                "date": request.date,
            }
            lines.append((0, 0, vals))
        res.update(
            {
                "employee_id": request.requested_by.employee_id.id,
                "user_id": request.approver_id.id,
                "expense_line_ids": lines,
                "name": request.reason,
            }
        )
        return res

    # --------------------------------------------
    # Server Actions after EX Action
    # --------------------------------------------

    def approve_expense_sheets(self):
        res = super().approve_expense_sheets()
        for rec in self.filtered(  # Use expense_sheet_ids, to detech EX and not AV
            lambda l: l in l.ref_request_id.expense_sheet_ids
        ):
            rec._run_doc_action("approved")
        return res

    def refuse_sheet(self, reason):
        res = super().refuse_sheet(reason)
        for rec in self.filtered(  # Use expense_sheet_ids, to detech EX and not AV
            lambda l: l in l.ref_request_id.expense_sheet_ids
        ):
            rec._run_doc_action("rejected")
        return res


class HRExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "request.doc.line.mixin"]

    ref_request_id = fields.Many2one(
        related="sheet_id.ref_request_id",
    )

    # --------------------------------------------
    # Values from request, when create new EX line
    # --------------------------------------------

    def _prepare_defaults(self):
        res = super()._prepare_defaults()
        return res
