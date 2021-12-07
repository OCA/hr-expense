# Copyright 2021 Ecosoft (<http://ecosoft.co.th>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class BaseSubstateType(models.Model):
    _inherit = "base.substate.type"

    model = fields.Selection(
        selection_add=[("hr.expense.sheet", "Expense Report")],
        ondelete={"hr.expense.sheet": "cascade"},
    )


class HrExpenseSheet(models.Model):
    _inherit = ["hr.expense.sheet", "base.substate.mixin"]
    _name = "hr.expense.sheet"
    _state_field = "state"
