# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    expense_sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        ondelete="set null",
        copy=False,
        index="btree_not_null",
    )
    show_commercial_partner_warning = fields.Boolean(
        compute="_compute_show_commercial_partner_warning"
    )

    @api.depends("commercial_partner_id")
    def _compute_show_commercial_partner_warning(self):
        for move in self:
            move.show_commercial_partner_warning = (
                move.commercial_partner_id == self.env.company.partner_id
                and move.move_type == "in_invoice"
                and move.partner_id.sudo().employee_ids
            )

    def action_open_expense_report(self):
        self.ensure_one()
        return self.expense_sheet_id._get_records_action()

    @api.ondelete(at_uninstall=True)
    def _must_delete_all_expense_entries(self):
        if (
            self.expense_sheet_id and self.expense_sheet_id.account_move_ids - self
        ):  # If not all the payments are to be deleted
            raise UserError(
                self.env._(
                    "You cannot delete only some entries linked to an expense report. "
                    "All entries must be deleted at the same time."
                )
            )
