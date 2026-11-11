# Copyright 2026 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrExpensePostWizard(models.TransientModel):
    _inherit = "hr.expense.post.wizard"

    @api.model
    def _default_general_journal_id(self):
        journal = self.env["account.journal"].search(
            [
                *self.env["account.journal"]._check_company_domain(self.env.company.id),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        return journal.id

    with_invoice = fields.Boolean(compute="_compute_with_invoice")
    without_invoice = fields.Boolean(compute="_compute_without_invoice")
    general_journal_id = fields.Many2one(
        comodel_name="account.journal",
        default=lambda self: self._default_general_journal_id(),
        check_company=True,
        domain=[("type", "=", "general")],
    )

    def _compute_with_invoice(self):
        expenses = self.env["hr.expense"].browse(self.env.context["active_ids"])
        for item in self:
            item.with_invoice = expenses and any(
                expense.invoice_id for expense in expenses
            )

    def _compute_without_invoice(self):
        expenses = self.env["hr.expense"].browse(self.env.context["active_ids"])
        for item in self:
            item.without_invoice = expenses and any(
                not expense.invoice_id for expense in expenses
            )

    def action_post_entry(self):
        expenses = self.env["hr.expense"].browse(self.env.context["active_ids"])
        expenses_with_invoices = expenses.filtered("invoice_id")
        expenses_without_invoices = expenses - expenses_with_invoices
        moves = moves_extra = move_model = self.env["account.move"]
        self = self.with_context(active_ids=expenses_without_invoices.ids)
        if expenses_without_invoices:
            res = super().action_post_entry()
            if not expenses_with_invoices:
                return res
            if "res_id" in res:
                moves = move_model.browse(res["res_id"])
            else:
                moves = move_model.search(res["domain"])
        if expenses_with_invoices:
            moves_extra = self._action_post_transfer_entry(expenses_with_invoices)
        return (moves_extra + moves)._get_records_action()

    def _action_post_transfer_entry(self, expenses):
        """We need to use a method other than action_post_entry() because that one
        does things we don't need:
        - It uses the employee_journal_id journal, which doesn't allow us to use
        type=general
        - It sets the invoice_date field instead of the date field
        - The _prepare_receipts_vals() method sets account.move`with a different
        move_type
        - It sets the company’s expense_journal_id field if employee_journal_id is
        set (which is completely incorrect if we were to set a journal with
        type=general there)
        """
        if not self.env["account.move"].has_access("create"):
            raise UserError(
                self.env._("You don't have the rights to create accounting entries.")
            )
        expense_transfer_vals_list = [
            {
                **new_transfer_vals,
                "journal_id": self.general_journal_id.id,
                "date": self.accounting_date,
            }
            for new_transfer_vals in expenses._prepare_transfers_vals()
        ]
        moves_sudo = self.env["account.move"].sudo().create(expense_transfer_vals_list)
        moves_sudo.action_post()
        moves_ids = moves_sudo.ids + self.env.context.get(
            "company_paid_move_ids", tuple()
        )
        return self.env["account.move"].browse(moves_ids)
