# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    @api.model_create_multi
    def create(self, vals_list):
        sequence_option_obj = self.env["ir.sequence.option.line"]
        for vals in vals_list:
            seq = sequence_option_obj.get_sequence(self.new(vals))
            self = self.with_context(sequence_option_id=seq.id)
            res = super().create(vals)
        return res
