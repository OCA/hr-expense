# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class RequestCategory(models.Model):
    _inherit = "request.category"

    use_ex = fields.Boolean(
        string="Use EX",
        compute="_compute_use_ex",
    )

    def _compute_use_ex(self):
        for rec in self:
            rec.use_ex = rec.child_doc_option_ids.filtered_domain(
                [("model", "=", "hr.expense.sheet")]
            )

    def _has_child_doc(self):
        return super()._has_child_doc() or self.use_ex


class RequestCategoryChildDocsOption(models.Model):
    _inherit = "request.category.child.doc.option"

    model = fields.Selection(
        selection_add=[("hr.expense.sheet", "Expense Sheet")],
        ondelete={"hr.expense.sheet": "cascade"},
    )
