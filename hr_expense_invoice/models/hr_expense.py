# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2020 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    sheet_id_state = fields.Selection(related="sheet_id.state", string="Sheet state")
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        domain=[
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "=", "not_paid"),
            ("expense_ids", "=", False),
        ],
        copy=False,
    )
    transfer_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="source_invoice_expense_id",
    )

    def _prepare_invoice_values(self):
        invoice_lines = [
            (
                0,
                0,
                {
                    "product_id": self.product_id.id,
                    "name": self.name,
                    "price_unit": self.untaxed_amount,
                    "quantity": self.quantity,
                    "account_id": self.account_id.id,
                    "analytic_distribution": self.analytic_distribution,
                    "tax_ids": [(6, 0, self.tax_ids.ids)],
                },
            )
        ]
        return {
            "name": "/",
            "ref": self.reference,
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "invoice_line_ids": invoice_lines,
        }

    def action_move_create(self):
        """Don't let super to create any move:
        - Paid by company: there's already the invoice.
        - Paid by employee: we create here a journal entry transferring the AP
          balance from the invoice partner to the employee.
        """
        expenses_with_invoice = self.filtered("invoice_id")
        res = super(HrExpense, self - expenses_with_invoice).action_move_create()
        # Create AP transfer entry for expenses paid by employees
        for expense in expenses_with_invoice:
            if expense.payment_mode == "own_account":
                move = self.env["account.move"].create(
                    expense._prepare_own_account_transfer_move_vals()
                )
                move.action_post()
                # reconcile with the invoice
                ap_lines = expense.invoice_id.line_ids.filtered(
                    lambda x: x.display_type == "payment_term"
                )
                transfer_line = move.line_ids.filtered(
                    lambda x: x.partner_id == self.invoice_id.partner_id
                )
                (ap_lines + transfer_line).reconcile()
        return res

    def _prepare_own_account_transfer_move_vals(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        # TODO: Allow to select a specific journal
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        employee_partner = self.employee_id.sudo().address_home_id.commercial_partner_id
        invoice_partner = self.invoice_id.partner_id
        ap_lines = self.invoice_id.line_ids.filtered(
            lambda x: x.display_type == "payment_term"
        )
        amount_invoice = sum(ap_lines.mapped("credit"))
        return {
            "journal_id": journal.id,
            "move_type": "entry",
            "name": "/",
            "date": self.date,
            "ref": self.name,
            "source_invoice_expense_id": self.id,
            "line_ids": [
                Command.create(
                    {
                        "account_id": ap_lines.account_id[:1].id,
                        "partner_id": invoice_partner.id,
                        "debit": amount_invoice,
                    }
                ),
                Command.create(
                    {
                        "account_id": employee_partner.property_account_payable_id.id,
                        "partner_id": employee_partner.id,
                        "credit": amount_invoice,
                    }
                ),
            ],
        }

    def action_expense_create_invoice(self):
        invoice = self.env["account.move"].create(self._prepare_invoice_values())
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )
        for attachment in attachments:
            attachment.copy({"res_model": invoice._name, "res_id": invoice.id})
        # Normalize data in the expense for avoiding mismatchings. Examples: the tax
        # reported is not correct, there's more than one concept, etc...
        self.write(
            {
                "invoice_id": invoice.id,
                "quantity": 1,
                "tax_ids": False,
                "unit_amount": invoice.amount_total,
            }
        )
        return True

    @api.constrains("invoice_id")
    def _check_invoice_id(self):
        for expense in self:  # Only non binding expense
            if (
                not expense.sheet_id
                and expense.invoice_id
                and expense.invoice_id.state != "posted"
            ):
                raise UserError(_("Vendor bill state must be Posted"))

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        """Assure quantity is 1 if an invoice is set for having proper totals, and
        the rest of the fields that are not computed writable, avoiding to ud
        """
        if self.invoice_id:
            self.quantity = 1
            self.reference = self.invoice_id.name
            self.date = self.invoice_id.date
            if self.invoice_id.company_id != self.company_id:
                # for avoiding to trigger dependent computes
                self.company_id = self.invoice_id.company_id.id

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
    @api.depends("invoice_id", "tax_ids")
    def _compute_unit_amount(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.unit_amount = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_unit_amount()

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
    @api.depends("invoice_id", "tax_ids")
    def _compute_amount(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.total_amount = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_amount()

    @api.depends("invoice_id")
    def _compute_currency_id(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.currency_id = record.invoice_id.currency_id.id
        return super(HrExpense, self - with_invoice)._compute_currency_id()

    @api.depends("invoice_id")
    def _compute_tax_ids(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.tax_ids = [(5,)]
        return super(HrExpense, self - with_invoice)._compute_tax_ids()

    @api.depends(
        "transfer_move_ids.line_ids.amount_residual",
        "transfer_move_ids.line_ids.amount_residual_currency",
    )
    def _compute_amount_residual(self):
        """Compute the amount residual for expenses paid by employee with invoices."""
        applicable_expenses = self.filtered(lambda x: x.transfer_move_ids)
        for rec in applicable_expenses:
            if not rec.currency_id or rec.currency_id == rec.company_currency_id:
                residual_field = "amount_residual"
            else:
                residual_field = "amount_residual_currency"
            payment_term_lines = rec.transfer_move_ids.sudo().line_ids.filtered(
                lambda x: x.account_type in ("asset_receivable", "liability_payable")
            )
            rec.amount_residual = -sum(payment_term_lines.mapped(residual_field))
        return super(HrExpense, self - applicable_expenses)._compute_amount_residual()
