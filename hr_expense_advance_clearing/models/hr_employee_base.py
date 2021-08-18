# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models


class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    advance_sheet_ids = fields.One2many(
        comodel_name="hr.expense.sheet",
        inverse_name="employee_id",
        domain=[("advance", "=", True)],
        readonly=True,
    )
    advance_count = fields.Integer(
        string="# of Advance",
        compute="_compute_advance_count",
        help="Count advance sheet in expense report",
    )

    def _compute_advance_count(self):
        self.advance_count = len(self.advance_sheet_ids)

    def action_open_advance_clearing(self):
        self.ensure_one()
        return {
            "name": _("Advance Sheet"),
            "type": "ir.actions.act_window",
            "res_model": "hr.expense.sheet",
            "view_mode": "tree,form",
            "domain": [("id", "in", self.advance_sheet_ids.ids)],
        }
