# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

from odoo.addons.request_flow.models.request_category import CATEGORY_SELECTION


class RequestCategory(models.Model):
    _inherit = "request.category"

    use_av = fields.Boolean(
        string="Use AV",
        compute="_compute_use_av",
    )
    has_av = fields.Selection(
        CATEGORY_SELECTION,
        string="Has Employee Advance",
        default="no",
        required=True,
        help="Option to select Employee Advance of the requester",
    )

    def _compute_use_av(self):
        for rec in self:
            rec.use_av = rec.child_doc_option_ids.filtered_domain(
                [("model", "=", "hr.advance.sheet")]
            )

    def _has_child_doc(self):
        return super()._has_child_doc() or self.use_av


class RequestCategoryChildDocsOption(models.Model):
    _inherit = "request.category.child.doc.option"

    model = fields.Selection(
        selection_add=[("hr.advance.sheet", "Advance Sheet")],
        ondelete={"hr.advance.sheet": "cascade"},
    )
