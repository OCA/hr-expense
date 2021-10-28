# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class RequestRequest(models.Model):
    _inherit = "request.request"

    use_ex = fields.Boolean(related="category_id.use_ex")
    hr_expense_count = fields.Integer(compute="_compute_hr_expense_count")
    expense_sheet_ids = fields.One2many(
        string="Expense Sheets",
        comodel_name="hr.expense.sheet",
        inverse_name="ref_request_id",
        copy=False,
    )

    def _ready_to_submit(self):
        if not super()._ready_to_submit():
            return False
        if not self.expense_sheet_ids:
            return True
        if self.expense_sheet_ids.filtered_domain(
            [("state", "not in", ["cancel", "submit"])]
        ):
            return False
        return True

    def _compute_hr_expense_count(self):
        for request in self:
            request.hr_expense_count = len(request.expense_sheet_ids)
