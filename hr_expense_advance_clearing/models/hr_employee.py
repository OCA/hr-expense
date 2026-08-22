# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    advance_expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="employee_id",
        domain=[("expense_type", "=", "advance")],
        readonly=True,
    )
    advance_count = fields.Integer(
        string="# of Advances",
        compute="_compute_advance_count",
        help="Count of advance expenses paid to this employee.",
    )

    def _compute_advance_count(self):
        for employee in self:
            employee.advance_count = len(employee.advance_expense_ids)

    def action_open_advance_clearing(self):
        self.ensure_one()
        return {
            "name": self.env._("Employee Advances"),
            "type": "ir.actions.act_window",
            "res_model": "hr.expense",
            "view_mode": "list,form",
            "domain": [("id", "in", self.advance_expense_ids.ids)],
        }


class HrEmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    advance_count = fields.Integer(related="employee_id.advance_count")

    def action_open_advance_clearing(self):
        self.ensure_one()
        return self.employee_id.action_open_advance_clearing()
