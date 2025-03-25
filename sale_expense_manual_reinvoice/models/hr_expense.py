# Copyright 2021 Camptocamp SA (https://www.camptocamp.com).
# @author Iván Todorovich <ivan.todorovich@camptocamp.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    analytic_line_ids = fields.One2many(
        "account.analytic.line", "expense_id", readonly=True
    )
    analytic_account_ids = fields.Many2many(
        "account.analytic.account",
        compute="_compute_analytic_account_ids",
        store=True,
    )
    manual_reinvoice = fields.Boolean(compute="_compute_manual_reinvoice", store=True)
    manual_reinvoice_done = fields.Boolean(
        compute="_compute_manual_reinvoice", store=True
    )
    manual_reinvoice_discarded = fields.Boolean(
        compute="_compute_manual_reinvoice", store=True
    )

    @api.depends(
        "analytic_line_ids",
        "analytic_line_ids.manual_reinvoice",
        "analytic_line_ids.manual_reinvoice_done",
        "analytic_line_ids.manual_reinvoice_discarded",
    )
    def _compute_manual_reinvoice(self):
        for rec in self:
            for fname in [
                "manual_reinvoice",
                "manual_reinvoice_done",
                "manual_reinvoice_discarded",
            ]:
                rec[fname] = fields.first(rec.analytic_line_ids)[fname]

    @api.depends("analytic_distribution")
    def _compute_analytic_account_ids(self):
        for rec in self:
            account_ids = (
                [int(acc_id) for acc_id in rec.analytic_distribution.keys()]
                if rec.analytic_distribution
                else []
            )
            rec.analytic_account_ids = self.env["account.analytic.account"].browse(
                account_ids
            )

    def action_manual_reinvoice(self):
        if any(not rec.sale_order_id for rec in self):
            raise UserError(
                _(
                    "Some expenses are missing the Customer to Reinvoice, "
                    "please fill this field on all lines and try again."
                )
            )
        return self.analytic_line_ids.action_manual_reinvoice()

    def action_manual_reinvoice_discard(self):
        self.analytic_line_ids.manual_reinvoice_discarded = True
        return True

    def action_manual_reinvoice_pending(self):
        self.analytic_line_ids.manual_reinvoice_discarded = False
        return True
