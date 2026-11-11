# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2020 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# Copyright 2026 Gray Matter Logic
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    sheet_id_state = fields.Selection(related="sheet_id.state", string="Sheet state")
    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        domain=(
            "[('move_type', '=', 'in_invoice'),"
            " ('state', '=', 'posted'),"
            " ('payment_state', '=', 'not_paid'),"
            " ('expense_ids', '=', False),"
            " ('partner_id', '=?', vendor_id)]"
        ),
        copy=False,
    )
    transfer_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="source_invoice_expense_id",
    )
    # This field has been added to reintroduce tracking for the amount due on each
    # expense, a feature that existed in previous versions. The tracking is necessary
    # to accurately reflect the payment state of the expense sheet.
    amount_residual = fields.Monetary(
        string="Amount Due", compute="_compute_amount_residual", store=True
    )

    def _prepare_invoice_values(self):
        self.ensure_one()
        invoice_lines = [
            Command.create(
                {
                    "product_id": self.product_id.id,
                    "name": self.name,
                    # Odoo considers always the amount taxes included, we need to take
                    # the base amount and quantity = 1
                    "price_unit": self.untaxed_amount_currency,
                    "quantity": 1,
                    "account_id": self.account_id.id,
                    "analytic_distribution": self.analytic_distribution,
                    "tax_ids": [Command.set(self.tax_ids.ids)],
                }
            )
        ]
        values = {
            "name": "/",
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "invoice_line_ids": invoice_lines,
        }
        if self.vendor_id:
            values["partner_id"] = self.vendor_id.id
        return values

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
        employee_partner = self.employee_id.sudo().work_contact_id
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
            "expense_sheet_id": self.sheet_id.id,
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
        self.ensure_one()
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

    def _sync_vendor_from_invoice(self):
        """Keep vendor_id aligned with the linked vendor bill partner."""
        if self.env.context.get("skip_vendor_invoice_sync"):
            return
        for expense in self.filtered(lambda rec: rec.invoice_id.partner_id):
            if expense.vendor_id != expense.invoice_id.partner_id:
                expense.with_context(skip_vendor_invoice_sync=True).write(
                    {"vendor_id": expense.invoice_id.partner_id.id}
                )

    @api.model_create_multi
    def create(self, vals_list):
        expenses = super().create(vals_list)
        expenses._sync_vendor_from_invoice()
        return expenses

    def write(self, vals):
        res = super().write(vals)
        if vals.get("invoice_id"):
            self._sync_vendor_from_invoice()
        return res

    @api.constrains("invoice_id")
    def _check_invoice_id(self):
        for expense in self:  # Only non binding expense
            if (
                not expense.sheet_id
                and expense.invoice_id
                and expense.invoice_id.state != "posted"
            ):
                raise UserError(self.env._("Vendor bill state must be Posted"))

    @api.constrains("invoice_id", "vendor_id")
    def _check_vendor_matches_invoice(self):
        for expense in self:
            partner = expense.invoice_id.partner_id
            if (
                expense.invoice_id
                and expense.vendor_id
                and partner
                and partner != expense.vendor_id
            ):
                raise UserError(
                    self.env._(
                        "The vendor and the vendor bill partner must be the same."
                    )
                )

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        """Assure quantity is 1 if an invoice is set for having proper totals, and
        the rest of the fields that are not computed writable, avoiding to ud
        """
        if self.invoice_id:
            self.quantity = 1
            self.name = self.name.split(" | ")[0].strip()
            self.name = "{} | {}".format(self.name or "", self.invoice_id.name)
            self.date = self.invoice_id.date
            if self.invoice_id.partner_id:
                self.vendor_id = self.invoice_id.partner_id
            if self.invoice_id.company_id != self.company_id:
                # for avoiding to trigger dependent computes
                self.company_id = self.invoice_id.company_id.id

    @api.onchange("vendor_id")
    def _onchange_vendor_id(self):
        """Selecting a different vendor drops a mismatched linked bill."""
        if (
            self.invoice_id
            and self.vendor_id
            and self.invoice_id.partner_id
            and self.invoice_id.partner_id != self.vendor_id
        ):
            self.invoice_id = False

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
    @api.depends("invoice_id", "tax_ids")
    def _compute_price_unit(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.price_unit = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_price_unit()

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
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

    @api.depends(
        "transfer_move_ids.line_ids.amount_residual",
        "transfer_move_ids.line_ids.amount_residual_currency",
    )
    def _compute_amount_residual(self):
        """Compute the amount residual for expenses paid by employee with invoices."""
        for rec in self:
            if not rec.currency_id or rec.currency_id == rec.company_currency_id:
                residual_field = "amount_residual"
            else:
                residual_field = "amount_residual_currency"
            payment_term_lines = rec.transfer_move_ids.sudo().line_ids.filtered(
                lambda x: x.account_type in ("asset_receivable", "liability_payable")
            )
            rec.amount_residual = -sum(payment_term_lines.mapped(residual_field))
