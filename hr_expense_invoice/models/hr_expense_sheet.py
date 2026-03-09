# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
from odoo.tools import config, float_compare


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    invoice_count = fields.Integer(compute="_compute_invoice_count")

    def get_expense_sheets_with_invoices(self, func):
        return self.filtered(
            lambda sheet: func(expense.invoice_id for expense in sheet.expense_line_ids)
        )

    def _do_create_ap_moves(self):
        # Create AP transfer entry for expenses paid by employees
        all_generated_moves = self.env["account.move"]
        for expense in self.expense_line_ids.filtered("invoice_id"):
            if expense.payment_mode == "own_account":
                move_vals = expense._prepare_own_account_transfer_move_vals()
                move = self.env["account.move"].create(move_vals)
                all_generated_moves |= move
        return all_generated_moves

    def _reconcile_ap_moves(self):
        # Reconcile AP transfer entries with vendor bills once they are posted
        for expense in self.expense_line_ids.filtered("invoice_id"):
            if expense.payment_mode == "own_account":
                move = self.account_move_ids.filtered(
                    lambda m, exp=expense: m.source_invoice_expense_id == exp
                )
                if move and move.state == "posted":
                    ap_lines = expense.invoice_id.line_ids.filtered(
                        lambda x: x.display_type == "payment_term"
                    )
                    transfer_line = move.line_ids.filtered(
                        lambda x, partner=expense.invoice_id.partner_id: x.partner_id
                        == partner
                    )
                    if ap_lines and transfer_line:
                        (ap_lines + transfer_line).reconcile()

    def _do_create_moves(self):
        removed_expenses_map = {}
        sheets_to_skip_super = self.env["hr.expense.sheet"]
        all_generated_moves = self.env["account.move"]
        for sheet in self:
            expenses_with_invoice = sheet.expense_line_ids.filtered("invoice_id")
            if expenses_with_invoice:
                if len(expenses_with_invoice) == len(sheet.expense_line_ids):
                    sheets_to_skip_super += sheet
                else:
                    removed_expenses_map[sheet.id] = expenses_with_invoice
                    sheet.expense_line_ids -= expenses_with_invoice
        sheets_for_super = self - sheets_to_skip_super
        if sheets_for_super:
            res = super(HrExpenseSheet, sheets_for_super)._do_create_moves()
            all_generated_moves |= res
        for sheet_id, expenses in removed_expenses_map.items():
            sheet = self.env["hr.expense.sheet"].browse(sheet_id)
            sheet.expense_line_ids += expenses
        ap_moves = self._do_create_ap_moves()
        all_generated_moves |= ap_moves
        return all_generated_moves

    def action_sheet_move_post(self):
        sheets_with_invoices = self.get_expense_sheets_with_invoices(any)
        sheets_all_invoices = self.get_expense_sheets_with_invoices(all)
        for sheet in sheets_with_invoices:
            sheet._validate_expense_invoice()
        res = super(HrExpenseSheet, self - sheets_all_invoices).action_sheet_move_post()
        for sheet in sheets_all_invoices:
            sheet._check_can_create_move()
            moves = sheet._do_create_moves()
            sheet.account_move_ids |= moves
            moves.action_post()
            sheet.filtered(
                lambda x: x.payment_mode == "company_account"
            )._compute_from_account_move_ids()
            if sheet.state == "approve" and sheet.account_move_ids:
                if sheet.payment_state in ["paid", "in_payment"]:
                    sheet.state = "done"
                else:
                    sheet.state = "post"
        sheets_mixed = sheets_with_invoices - sheets_all_invoices
        if sheets_mixed:
            sheets_mixed.filtered(
                lambda x: x.payment_mode == "company_account"
            )._compute_from_account_move_ids()
        for sheet in sheets_with_invoices:
            sheet._reconcile_ap_moves()
        return res

    def set_to_paid(self):
        """Don't mark sheet as paid when reconciling invoices."""
        if self.env.context.get("use_hr_expense_invoice"):
            return True
        return super().set_to_paid()

    def _compute_invoice_count(self):
        Invoice = self.env["account.move"]
        can_read = Invoice.has_access("read")
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

    def _prepare_bills_vals(self):
        res = super()._prepare_bills_vals()
        test_condition = not config["test_enable"] or self.env.context.get(
            "test_hr_expense_invoice"
        )
        if test_condition:
            expenses_without_invoice = self.expense_line_ids.filtered(
                lambda r: not r.invoice_id
            )
            res["line_ids"] = [
                Command.create(expense._prepare_move_lines_vals())
                for expense in expenses_without_invoice
            ]
        return res

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
            raise UserError(self.env._("Vendor bill state must be Posted"))
        expense_amount = sum(expense_lines.mapped("total_amount_currency"))
        invoice_amount = sum(invoices.mapped("amount_total"))
        # Expense amount must equal invoice amount
        if float_compare(expense_amount, invoice_amount, precision) != 0:
            raise UserError(
                self.env._(
                    "Vendor bill amount mismatch!\nPlease make sure amount in "
                    "vendor bills equal to amount of its expense lines"
                )
            )

    def action_view_invoices(self):
        self.ensure_one()
        action = {
            "name": self.env._("Invoices"),
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
            action["view_mode"] = "list,form"
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

    def _do_approve(self):
        expense_sheets_with_invoices = self.get_expense_sheets_with_invoices(all)
        own_account_sheets = self.filtered(
            lambda sheet: sheet.payment_mode == "own_account"
        )
        sheets_to_bypass = expense_sheets_with_invoices + own_account_sheets
        res = super(HrExpenseSheet, self - sheets_to_bypass)._do_approve()
        for sheet in sheets_to_bypass.filtered(
            lambda s: s.state in {"submit", "draft"}
        ):
            sheet.write(
                {
                    "approval_state": "approve",
                    "user_id": sheet.user_id.id or self.env.user.id,
                    "approval_date": fields.Date.context_today(sheet),
                }
            )
            self.activity_update()
        return res

    def _track_subtype(self, init_values):
        self.ensure_one()
        if self.state == "approve":
            return self.env.ref("hr_expense_invoice.mt_expense_approved_inherited")
        else:
            super()._track_subtype(init_values)

    def _check_can_create_move(self):
        expense_sheets_with_invoices = self.get_expense_sheets_with_invoices(all)
        res = super(
            HrExpenseSheet, self - expense_sheets_with_invoices
        )._check_can_create_move()
        # We copy this method because the expenses are in 'approve' or 'posted'
        # in case this is the second run, instead of 'submit'
        if any(not sheet.expense_line_ids for sheet in expense_sheets_with_invoices):
            raise UserError(
                self.env._(
                    "You cannot create accounting entries for an expense \
                        report without expenses."
                )
            )
        if any(
            sheet.state not in ["approve", "post"]
            for sheet in expense_sheets_with_invoices
        ):
            raise UserError(
                self.env._(
                    "You can only generate an accounting entry for approved expense(s)."
                )
            )
        if any(not sheet.journal_id for sheet in expense_sheets_with_invoices):
            raise UserError(
                self.env._(
                    "Please specify an expense journal in order to generate \
                        accounting entries."
                )
            )
        if False in expense_sheets_with_invoices.mapped("payment_mode"):
            raise UserError(
                self.env._(
                    "Please specify if the expenses for this report were paid by \
                        the company, or the employee"
                )
            )
        missing_email_employees = expense_sheets_with_invoices.filtered(
            lambda sheet: not sheet.employee_id.work_email
        ).employee_id
        if missing_email_employees:
            action = expense_sheets_with_invoices.env["ir.actions.actions"]._for_xml_id(
                "hr.open_view_employee_list_my"
            )
            action["domain"] = [("id", "in", missing_email_employees.ids)]
            raise RedirectWarning(
                self.env._(
                    "The work email of some employees is missing. Please add it on \
                         the employee form"
                ),
                action,
                self.env._("Show missing work email employees"),
            )
        return res
