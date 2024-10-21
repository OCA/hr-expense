# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    invoice_count = fields.Integer(compute="_compute_invoice_count")

    def _do_create_moves(self):
        """Don't let super to create any move:
        - Paid by company: there's already the invoice.
        - Paid by employee: we create here a journal entry transferring the AP
          balance from the invoice partner to the employee.
        """
        expense_sheets_with_invoices = self.filtered(
            lambda sheet: all(expense.invoice_id for expense in sheet.expense_line_ids)
        )
        res = super(
            HrExpenseSheet, self - expense_sheets_with_invoices
        )._do_create_moves()
        # Create AP transfer entry for expenses paid by employees
        for expense in expense_sheets_with_invoices.expense_line_ids:
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
                    lambda x: x.partner_id
                    == expense.invoice_id.partner_id
                )
                (ap_lines + transfer_line).reconcile()
        return res

    def action_sheet_move_create(self):
        """Perform extra checks and set proper payment state according linked
        invoices.
        """
        self._validate_expense_invoice()
        res = super().action_sheet_move_create()
        # The payment state is set in a fixed way in super, but it depends on the
        # payment state of the invoices when there are some of them linked
        self.filtered(
            lambda x: x.expense_line_ids.invoice_id
            and x.payment_mode == "company_account"
        )._compute_from_account_move_ids()
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
    def _compute_from_account_move_ids(self):
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
        return super(
            HrExpenseSheet, self - invoice_sheets
        )._compute_from_account_move_ids()

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
        expense_amount = sum(expense_lines.mapped("total_amount_currency"))
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

    @api.depends()
    def _compute_state(self):
        """Set proper state according to linked invoices."""
        sheets_with_invoices = self.filtered(
            lambda sheet: all(
                expense.invoice_id and expense.invoice_id.state == "posted"
                for expense in sheet.expense_line_ids
            )
            and sheet.state == sheet.approval_state
        )

        company_account_sheets = sheets_with_invoices.filtered(
            lambda sheet: sheet.payment_mode == "company_account"
        )
        company_account_sheets.state = "done"

        sheets_with_paid_invoices = (
            sheets_with_invoices - company_account_sheets
        ).filtered(
            lambda sheet: all(
                expense.invoice_id.payment_state != "not_paid"
                for expense in sheet.expense_line_ids
            )
        )
        sheets_with_paid_invoices.state = "post"

        return super(HrExpenseSheet, self - sheets_with_invoices)._compute_state()
