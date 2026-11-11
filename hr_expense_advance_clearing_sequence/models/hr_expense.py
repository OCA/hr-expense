# Copyright 2019 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import api, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    @api.model_create_multi
    def create(self, vals_list):
        default_advance = self.env.context.get("default_advance")
        # base_sequence_option's next_by_code ignores the code it is given when
        # sequence_option_id is in the context, so an expense sequence option
        # would hand out its own numbers here instead of the advance ones.
        sequence = self.env["ir.sequence"].with_context(sequence_option_id=False)
        for vals in vals_list:
            if vals.get("advance", default_advance) and vals.get("number", "/") == "/":
                vals["number"] = (
                    sequence.next_by_code("hr.expense.sheet.advance") or "/"
                )
        return super().create(vals_list)
