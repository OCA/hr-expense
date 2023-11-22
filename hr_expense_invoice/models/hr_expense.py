# Copyright 2015-2020 Tecnativa - Pedro M. Baeza
# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2020 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
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
    with_invoice_id = fields.Boolean(
        compute="_compute_with_invoice_id", compute_sudo=True, store=True
    )

    @api.depends("invoice_id")
    def _compute_with_invoice_id(self):
        for item in self:
            item.with_invoice_id = bool(item.invoice_id)

    def _prepare_invoice_values(self):
        invoice_lines = [
            (
                0,
                0,
                {
                    "product_id": self.product_id.id,
                    "name": self.name,
                    "price_unit": self.unit_amount or self.total_amount,
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
        """It overrides the journal item values to match the invoice payable one."""
        res = super().action_move_create()
        for item in self.filtered(lambda x: x.invoice_id):
            invoice = item.invoice_id
            debit_move_line = res.line_ids.filtered(
                lambda x: x.expense_id == item and x.debit
            )
            debit_move_line.partner_id = invoice.partner_id.commercial_partner_id
            debit_move_line.account_id = invoice.line_ids.filtered(
                lambda x: x.account_type == "liability_payable"
            ).account_id
        return res

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
        """Get expense amount from invoice amount. Otherwise it will do a
        mismatch when trying to post the account move. We do that ensuring we
        have the same total amount with quantity 1 and without taxes.
        """
        if self.invoice_id:
            self.quantity = 1
            self.product_uom_id = self.product_id.uom_id
            self.tax_ids = [(5,)]
            # Assign this amount after removing taxes for avoiding to raise
            # the constraint _check_expense_ids
            self.unit_amount = self.invoice_id.amount_total
