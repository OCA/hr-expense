# Copyright 2021 Ecosoft Co., Ltd. (https://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.model_create_multi
    def create(self, vals_list):
        sequence_option_obj = self.env["ir.sequence.option.line"]
        records = self.browse()
        for vals in vals_list:
            seq = sequence_option_obj.get_sequence(self.new(vals))
            records |= super(
                HrExpense, self.with_context(sequence_option_id=seq.id)
            ).create([vals])
        return records
