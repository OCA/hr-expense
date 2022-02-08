# Copyright 2021 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    expense_id = fields.Many2one(
        related="move_id.expense_id",
        store=True,
    )
    manual_reinvoice = fields.Boolean(
        compute="_compute_manual_reinvoice",
        store=True,
    )
    manual_reinvoice_done = fields.Boolean(
        compute="_compute_manual_reinvoice_done",
        store=True,
    )
    manual_reinvoice_discarded = fields.Boolean(
        help="Technical field to hide it from pending to reinvoice list."
    )

    @api.depends("product_id")
    def _compute_manual_reinvoice(self):
        for rec in self:
            rec.manual_reinvoice = rec.expense_id.product_id.expense_mode == "manual"

    @api.depends("manual_reinvoice", "so_line")
    def _compute_manual_reinvoice_done(self):
        for rec in self:
            rec.manual_reinvoice_done = rec.manual_reinvoice and rec.so_line

    def action_manual_reinvoice(self):
        if any(not rec.manual_reinvoice for rec in self):
            raise UserError(_("Only manually re-invoice expenses can be re-invoiced."))
        if any(rec.manual_reinvoice_done for rec in self):
            raise UserError(_("Expense already re-invoiced."))
        sale_lines_per_move_id = self.move_id._sale_create_reinvoice_sale_line()
        for rec in self:
            sale_line = sale_lines_per_move_id.get(rec.move_id.id)
            if sale_line:
                rec.so_line = sale_line
            if rec.manual_reinvoice_discarded:
                rec.manual_reinvoice_discarded = False
