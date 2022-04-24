# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.model
    def _get_under_validation_exceptions(self):
        """Extend for more field exceptions."""
        return ["message_follower_ids", "access_token"]

    def _check_allow_write_under_validation(self, vals):
        """Allow to add exceptions for fields that are allowed to be written
        even when the record is under validation."""
        exceptions = self._get_under_validation_exceptions()
        if any(val not in exceptions for val in vals):
            return False
        return True

    def write(self, vals):
        for rec in self:
            if (
                rec.sheet_id.state == "submit"
                and rec.sheet_id.review_ids
                and not rec.sheet_id.validated
                and not rec.sheet_id.rejected
                and not rec._check_allow_write_under_validation(vals)
            ):
                raise ValidationError(_("The expense report is under validation."))
        return super().write(vals)
