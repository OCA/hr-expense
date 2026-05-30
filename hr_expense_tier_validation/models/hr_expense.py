# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import api, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "tier.validation"]

    _state_field = "approval_state"
    _state_from = ["submitted"]
    _state_to = ["approved"]

    _tier_validation_manual_config = False

    @api.model
    def _get_under_validation_exceptions(self):
        """Extend for more field exceptions."""
        params_exception = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hr_expense.tier_exceptions")
            or []
        )
        # Convert to list
        if not isinstance(params_exception, list):
            params_exception = ast.literal_eval(params_exception)
        return params_exception

    def _check_allow_write_under_validation(self, vals):
        """Allow to add exceptions for fields that are allowed to be written
        or for reviewers for all fields, even when the record is under
        validation."""
        exceptions = self._get_under_validation_exceptions()
        for val in vals:
            if val not in exceptions:
                return False
        return True

    def write(self, vals):
        for rec in self:
            if (
                rec.approval_state == "submitted"
                and rec.review_ids
                and rec.validation_status not in ("validated", "rejected")
                and not rec._check_allow_write_under_validation(vals)
            ):
                raise ValidationError(self.env._("The expense is under validation."))
        return super().write(vals)
