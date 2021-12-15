# Copyright 2021 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    expense_mode = fields.Selection(
        [("auto", "Automatically"), ("manual", "Manually")],
        string="Re-invoice Mode",
        default="auto",
        help="Choose how to re-invoice expenses:\n\n"
        "* Automatically: Expenses are automatically re-invoiced when they're posted.\n"
        "* Manually: Expenses have to be manually re-invoiced by a manager.\n",
    )
