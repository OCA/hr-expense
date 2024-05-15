# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    invoice_count = fields.Integer(compute="_compute_invoice_count")

    def action_sheet_move_create(self):
        """Perform extra checks and set proper state and payment state according linked
        invoices.
        """
        self._validate_expense_invoice()
        res = super().action_sheet_move_create()
        # The payment state is set in a fixed way in super, but it depends on the
        # payment state of the invoices when there are some of them linked
        self.filtered(
            lambda x: x.expense_line_ids.invoice_id
            and x.payment_mode == "company_account"
        )._compute_payment_state()
        return res

    def set_to_paid(self):
        """Don't mark sheet as paid when reconciling invoices."""
        if self.env.context.get("use_hr_expense_invoice"):
            return True
        return super().set_to_paid()

    def _compute_invoice_count(self):
        Invoice = self.env["account.move"]
        can_read = Invoice.check_access_rights("read", raise_exception=False)
        for sheet in self:
            sheet.invoice_count = (
                can_read and len(sheet.expense_line_ids.mapped("invoice_id")) or 0
            )

    @api.depends(
        "expense_line_ids.invoice_id.payment_state",
        "expense_line_ids.amount_residual",
    )
    def _compute_payment_state(self):
        """Determine the payment status for lines with expense invoices linked"""
        invoice_sheets = self.filtered(lambda x: x.expense_line_ids.invoice_id)
        invoice_sheets.payment_state = "not_paid"
        for sheet in invoice_sheets:
            lines = sheet.expense_line_ids
            lines_with_invoices = len(lines.filtered("invoice_id"))
            if sheet.payment_mode == "company_account":
                lines_with_paid_invoices = len(
                    lines.filtered(lambda x: x.invoice_id.payment_state == "paid")
                )
                lines_with_partial_invoices = len(
                    lines.filtered(lambda x: x.invoice_id.payment_state == "partial")
                )
            else:
                lines_with_paid_invoices = len(
                    lines.filtered(
                        lambda x: x.transfer_move_ids and x.amount_residual == 0
                    )
                )
                lines_with_partial_invoices = 0  # TODO: Consider partial reconciliation
            if lines_with_invoices == lines_with_paid_invoices:
                sheet.payment_state = "paid"
            elif lines_with_paid_invoices or lines_with_partial_invoices:
                sheet.payment_state = "partial"
        return super(HrExpenseSheet, self - invoice_sheets)._compute_payment_state()

    def _validate_expense_invoice(self):
        """Check several criteria that needs to be met for creating the move."""
        expense_lines = self.mapped("expense_line_ids").filtered("invoice_id")
        DecimalPrecision = self.env["decimal.precision"]
        precision = DecimalPrecision.precision_get("Product Price")
        invoices = expense_lines.mapped("invoice_id")
        if not invoices:
            return
        # All invoices must confirmed
        if any(invoices.filtered(lambda i: i.state != "posted")):
            raise UserError(_("Vendor bill state must be Posted"))
        expense_amount = sum(expense_lines.mapped("total_amount"))
        invoice_amount = sum(invoices.mapped("amount_total"))
        # Expense amount must equal invoice amount
        if float_compare(expense_amount, invoice_amount, precision) != 0:
            raise UserError(
                _(
                    "Vendor bill amount mismatch!\nPlease make sure amount in "
                    "vendor bills equal to amount of its expense lines"
                )
            )

    def action_view_invoices(self):
        self.ensure_one()
        action = {
            "name": _("Invoices"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "target": "current",
        }
        invoice_ids = self.expense_line_ids.mapped("invoice_id").ids
        view = self.env.ref("account.view_move_form")
        if len(invoice_ids) == 1:
            invoice = invoice_ids[0]
            action["res_id"] = invoice
            action["view_mode"] = "form"
            action["views"] = [(view.id, "form")]
        else:
            action["view_mode"] = "tree,form"
            action["domain"] = [("id", "in", invoice_ids)]
        return action
