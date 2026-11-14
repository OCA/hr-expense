# Copyright 2026 Ecosoft Co., Ltd (https://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from odoo import fields, models
from odoo.exceptions import UserError


class HrExpensePostWizard(models.TransientModel):
    _inherit = "hr.expense.post.wizard"

    is_advance_clearing = fields.Boolean(
        default=lambda self: bool(self.env.context.get("advance_clearing"))
    )
    clearing_journal_id = fields.Many2one(
        comodel_name="account.journal",
        default=lambda self: self.env.company.clearing_journal_id,
        check_company=True,
    )

    def action_post_entry(self):
        if not self.is_advance_clearing:
            return super().action_post_entry()

        expenses = (
            self.env["hr.expense"]
            .browse(self.env.context.get("active_ids", []))
            .exists()
        )
        if not expenses or any(not expense.advance_id for expense in expenses):
            raise UserError(
                self.env._(
                    "The clearing journal can only be used for advance "
                    "clearing expenses."
                )
            )
        if not self.env["account.move"].has_access("create"):
            raise UserError(
                self.env._("You don't have the rights to create accounting entries.")
            )
        if not self.clearing_journal_id:
            raise UserError(
                self.env._(
                    "Please configure a Default Clearing Journal "
                    "in the Expense settings."
                )
            )

        moves = expenses._create_advance_clearing_moves(
            self.clearing_journal_id,
            self.accounting_date,
        )
        moves.action_post()
        expenses._reconcile_advance_moves()

        if not self.company_id.clearing_journal_id:
            self.sudo().company_id.clearing_journal_id = self.clearing_journal_id

        action = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
        }
        if len(moves) == 1:
            action.update(
                {
                    "name": moves.ref,
                    "view_mode": "form",
                    "res_id": moves.id,
                }
            )
        else:
            list_view = self.env.ref(
                "hr_expense.view_move_list_expense",
                raise_if_not_found=False,
            )
            action.update(
                {
                    "name": self.env._("New advance clearing entries"),
                    "view_mode": "list,form",
                    "views": [
                        (list_view and list_view.id, "list"),
                        (False, "form"),
                    ],
                    "domain": [("id", "in", moves.ids)],
                }
            )
        return action
