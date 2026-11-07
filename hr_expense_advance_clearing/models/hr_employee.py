# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    advance_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="employee_id",
        domain=[("advance", "=", True)],
        readonly=True,
    )
    advance_count = fields.Integer(
        string="# of Advance",
        compute="_compute_advance_count",
        help="Count advances",
    )

    @api.depends("advance_ids")
    def _compute_advance_count(self):
        self.advance_count = len(self.advance_ids)

    def action_open_advance_clearing(self):
        self.ensure_one()
        return {
            "name": self.env._("Advance"),
            "type": "ir.actions.act_window",
            "res_model": "hr.expense",
            "view_mode": "list,form",
            "domain": [("id", "in", self.advance_ids.ids)],
        }
