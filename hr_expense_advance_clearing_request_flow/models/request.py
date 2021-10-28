# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class RequestRequest(models.Model):
    _inherit = "request.request"

    # AV
    use_av = fields.Boolean(related="category_id.use_av")
    hr_advance_count = fields.Integer(compute="_compute_hr_advance_count")
    advance_sheet_ids = fields.One2many(
        string="Advance Sheets",
        comodel_name="hr.expense.sheet",
        inverse_name="ref_request_id",
        domain=[("advance", "=", True)],
        copy=False,
    )
    expense_sheet_ids = fields.One2many(
        domain=[("advance", "=", False)],
    )
    # Clear AV
    has_av = fields.Selection(related="category_id.has_av")
    advance_sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        string="Clear Advance",
        domain="[('advance', '=', True),('employee_id.user_id', '=', requested_by),"
        "('clearing_residual', '>', 0.0)]",
        copy=False,
        help="Target Employee advance to be cleared by this EX.",
    )

    def _ready_to_submit(self):
        if not super()._ready_to_submit():
            return False
        if not self.advance_sheet_ids:
            return True
        if self.advance_sheet_ids.filtered_domain(
            [("state", "not in", ["cancel", "submit"])]
        ):
            return False
        return True

    def _compute_hr_advance_count(self):
        for request in self:
            request.hr_advance_count = len(request.advance_sheet_ids)

    def _filtered_domain_child_doc(self, model):
        domain = super()._filtered_domain_child_doc(model)
        if model == "hr.expense.sheet":
            if self.env.context.get("use_av"):
                domain.append(("advance", "=", True))
            else:
                domain.append(("advance", "=", False))
        return domain

    def view_child_doc(self):
        action = super().view_child_doc()
        self._set_has_av_context(action)
        return action

    def _prepare_advance_line(self):
        advance = self.env.ref("hr_expense_advance_clearing.product_emp_advance")
        return {
            "advance": True,
            "product_id": advance.id,
            "employee_id": self.requested_by.employee_id.id,
            "payment_mode": "own_account",
        }

    def create_child_doc(self):
        action = super().create_child_doc()
        # Cleanup before reassign
        action["context"]["default_expense_line_ids"] = False
        action["context"]["request_advance_amount"] = False
        # For AV, also create advance line
        if self.env.context.get("use_av"):
            av_line = [(0, 0, self._prepare_advance_line())]
            action["context"]["default_expense_line_ids"] = av_line
            action["context"]["request_advance_amount"] = self.amount
        self._set_has_av_context(action)
        return action

    def _set_has_av_context(self, action):
        """ Context to control invisibility of advance_sheet_id """
        action["context"]["has_av"] = True if self.has_av != "no" else False
        return action
