# Copyright 2021 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _sale_can_be_reinvoice(self):
        # OVERRIDE to skip automatic reinvoicing of expense lines, when needed
        res = super()._sale_can_be_reinvoice()
        if self.expense_id:
            return self.expense_id.product_id.expense_mode != "manual" and res
        return res
