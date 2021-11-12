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
            ("type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("invoice_payment_state", "=", "not_paid"),
            ("expense_ids", "=", False),
        ],
        copy=False,
    )

    def action_expense_create_invoice(self):
        invoice_lines = [
            (
                0,
                0,
                {
                    "product_id": self.product_id.id,
                    "name": self.name,
                    "price_unit": self.unit_amount,
                    "quantity": self.quantity,
                    "account_id": self.account_id.id,
                    "analytic_account_id": self.analytic_account_id.id,
                    "tax_ids": [(6, 0, self.tax_ids.ids)],
                },
            )
        ]
        invoice = (
            self.env["account.move"]
            .with_context(default_type="in_invoice")
            .create(
                {
                    "ref": self.reference,
                    "invoice_date": self.date,
                    "invoice_line_ids": invoice_lines,
                }
            )
        )
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

    def _get_account_move_line_values(self):
        """It overrides the journal item values to match the invoice payable one."""
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense_id, move_lines in move_line_values_by_expense.items():
            expense = self.browse(expense_id)
            if not expense.invoice_id:
                continue
            for move_line in move_lines:
                if move_line["debit"]:
                    move_line[
                        "partner_id"
                    ] = expense.invoice_id.partner_id.commercial_partner_id.id
                    move_line["account_id"] = expense.invoice_id.line_ids.filtered(
                        lambda l: l.account_internal_type == "payable"
                    ).account_id.id
        return move_line_values_by_expense

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        """Get expense amount from invoice amount. Otherwise it will do a
        mismatch when trying to post the account move. We do that ensuring we
        have the same total amount with quantity 1 and without taxes.
        """
        if self.invoice_id:
            self.quantity = 1
            self.tax_ids = [(5,)]
            # Assign this amount after removing taxes for avoiding to raise
            # the constraint _check_expense_ids
            self.unit_amount = self.invoice_id.amount_total
