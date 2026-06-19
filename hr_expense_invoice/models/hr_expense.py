# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2020 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrExpense(models.Model):
    _inherit = "hr.expense"

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        domain=[
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "=", "not_paid"),
            # Exclude bills already linked to another expense.
            ("invoice_expense_ids", "=", False),
        ],
        copy=False,
    )
    transfer_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="source_invoice_expense_id",
    )

    def _prepare_invoice_values(self):
        invoice_lines = [
            Command.create(
                {
                    "product_id": self.product_id.id,
                    "name": self.name,
                    "price_unit": self.untaxed_amount_currency,
                    "quantity": 1,
                    "account_id": self.account_id.id,
                    "analytic_distribution": self.analytic_distribution,
                    "tax_ids": [Command.set(self.tax_ids.ids)],
                }
            )
        ]
        return {
            "name": "/",
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "invoice_line_ids": invoice_lines,
        }

    def action_expense_create_invoice(self):
        invoice = self.env["account.move"].create(self._prepare_invoice_values())
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )
        for attachment in attachments:
            attachment.copy({"res_model": invoice._name, "res_id": invoice.id})
        self.write(
            {
                "invoice_id": invoice.id,
                "quantity": 1,
                "tax_ids": False,
                "price_unit": invoice.amount_total,
            }
        )
        return True

    @api.constrains("invoice_id")
    def _check_invoice_id(self):
        # Allow draft bills while the expense is draft; posting is gated by
        # _validate_expense_invoice() at action_post time.
        for expense in self:
            if (
                expense.state != "draft"
                and expense.invoice_id
                and expense.invoice_id.state != "posted"
            ):
                raise UserError(self.env._("Vendor bill state must be Posted"))

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        if self.invoice_id:
            self.quantity = 1
            self.name = (self.name or "").split(" | ")[0].strip()
            self.name = f"{self.name} | {self.invoice_id.name}"
            self.date = self.invoice_id.date
            if self.invoice_id.company_id != self.company_id:
                self.company_id = self.invoice_id.company_id.id

    @api.depends("invoice_id", "tax_ids")
    def _compute_price_unit(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.price_unit = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_price_unit()

    @api.depends("invoice_id", "tax_ids")
    def _compute_total_amount_currency(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.total_amount_currency = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_total_amount_currency()

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

    def action_post(self):
        """Route bill-linked expenses through the transfer-entry flow instead
        of core's auto-generated receipt; let the rest fall through to super."""
        bill_linked = self.filtered("invoice_id")
        regular = self - bill_linked
        bill_linked._validate_expense_invoice()
        res = super(HrExpense, regular).action_post() if regular else None
        own_account_bill_linked = bill_linked.filtered(
            lambda e: e.payment_mode == "own_account"
        )
        for expense in own_account_bill_linked:
            move_vals = expense._prepare_own_account_transfer_move_vals()
            move = self.env["account.move"].create(move_vals)
            move.action_post()
            expense._reconcile_ap_move(move)
        # Company-paid bill-linked: the bill is already the company's debt, so
        # no transfer entry is needed; just mark the expense approved.
        company_bill_linked = bill_linked - own_account_bill_linked
        if company_bill_linked:
            company_bill_linked.sudo().write({"approval_state": "approved"})
        return res

    def _validate_expense_invoice(self):
        """Validate that linked bills are posted and amounts match."""
        if not self:
            return
        DecimalPrecision = self.env["decimal.precision"]
        precision = DecimalPrecision.precision_get("Product Price")
        for expense in self:
            invoice = expense.invoice_id
            if invoice.state != "posted":
                raise UserError(self.env._("Vendor bill state must be Posted"))
            if (
                float_compare(
                    expense.total_amount_currency, invoice.amount_total, precision
                )
                != 0
            ):
                raise UserError(
                    self.env._(
                        "Vendor bill amount mismatch!\nPlease make sure the "
                        "vendor bill total equals the expense total."
                    )
                )

    def _prepare_own_account_transfer_move_vals(self):
        self.ensure_one()
        rec = self.with_company(self.company_id)
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", rec.company_id.id),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        employee_partner = rec.employee_id.sudo().work_contact_id
        invoice_partner = rec.invoice_id.partner_id
        ap_lines = rec.invoice_id.line_ids.filtered(
            lambda x: x.display_type == "payment_term"
        )
        amount_invoice = sum(ap_lines.mapped("credit"))
        return {
            "journal_id": journal.id,
            "move_type": "entry",
            "name": "/",
            "date": rec.date,
            "ref": rec.name,
            "source_invoice_expense_id": rec.id,
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

    def _reconcile_ap_move(self, move):
        """Reconcile the transfer entry with the bill so paying the bill
        clears the employee's portion."""
        self.ensure_one()
        invoice = self.invoice_id
        ap_lines = invoice.line_ids.filtered(lambda x: x.display_type == "payment_term")
        transfer_line = move.line_ids.filtered(
            lambda x: x.partner_id == invoice.partner_id
        )
        if ap_lines and transfer_line:
            (ap_lines + transfer_line).reconcile()

    @api.depends(
        "transfer_move_ids.line_ids.amount_residual",
        "transfer_move_ids.line_ids.amount_residual_currency",
    )
    def _compute_amount_residual(self):
        """For bill-linked expenses, derive the residual from the transfer
        entry's open balance instead of the receipt's."""
        with_invoice = self.filtered("invoice_id")
        for rec in with_invoice:
            if not rec.currency_id or rec.currency_id == rec.company_currency_id:
                residual_field = "amount_residual"
            else:
                residual_field = "amount_residual_currency"
            payment_term_lines = rec.transfer_move_ids.sudo().line_ids.filtered(
                lambda x: x.account_type in ("asset_receivable", "liability_payable")
            )
            rec.amount_residual = -sum(payment_term_lines.mapped(residual_field))
        return super(HrExpense, self - with_invoice)._compute_amount_residual()
