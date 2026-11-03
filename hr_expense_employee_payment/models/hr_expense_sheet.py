# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import Command, api, exceptions, models
from odoo.tools import float_compare, float_is_zero


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _get_vendor_moves(self, for_employee=False):
        """Get the vendor bills linked to selected expense sheets.

        :param for_employee: True: Bills for the employee. False: Bills for the vendor.
        :return: A recordset of account.move matching vendor or employee bills.
        """
        entry_moves = self.account_move_ids.filtered_domain(
            [("move_type", "!=", "entry")]
        )
        vendor_moves = entry_moves.filtered(
            lambda move: move.partner_id
            != move.expense_sheet_id.employee_id.sudo().work_contact_id
        )
        if for_employee:
            return entry_moves - vendor_moves
        return vendor_moves

    def _get_vendor_payable_move_lines(self):
        """Get the payable move lines from the vendor
        bills linked to selected expense sheets."""
        vendor_bills = self._get_vendor_moves(for_employee=False)
        return vendor_bills.mapped("line_ids").filtered(
            lambda line: line.display_type == "payment_term"
            and not float_is_zero(
                line.amount_residual, precision_rounding=line.currency_id.rounding
            )
        )

    def _get_conciliation_moves(self, posted=False):
        """Obtain the conciliation entries for selected expense sheets, if any.

        :param posted: If True, only posted moves are returned.
        :return: A recordset of account.move matching conciliation entries.
        """
        conciliation_moves = self.env["account.move"].browse()
        valid_states = ["posted"] if posted else ["draft", "cancel", "posted"]
        for sheet in self:
            conciliation_moves |= sheet.account_move_ids.filtered_domain(
                [
                    ("move_type", "=", "entry"),
                    ("state", "in", valid_states),
                ]
            )
        return conciliation_moves

    def _get_conciliation_payable_move_lines(self, for_employee=False):
        """Obtain the posted payable move lines from the conciliation entries
        for selected expense sheets.

        :param for_employee: True: Lines for the employee. False: Lines for the vendor.
        :return: A recordset of account.move.line matching conciliation payable lines.
        """
        conciliation_payable_lines = self.env["account.move.line"].browse()
        for conciliation_move in self._get_conciliation_moves(posted=True):
            employee_partner = (
                conciliation_move.expense_sheet_id.employee_id.sudo().work_contact_id
            )
            conciliation_payable_employee_lines = (
                conciliation_move.line_ids.filtered_domain(
                    [
                        ("partner_id", "=", employee_partner.id),
                    ]
                )
            )
            if for_employee:
                conciliation_payable_lines |= conciliation_payable_employee_lines
            else:
                conciliation_payable_lines |= (
                    conciliation_move.line_ids - conciliation_payable_employee_lines
                )
        return conciliation_payable_lines

    def _prepare_conciliation_move_vals(self):
        """Prepare the values for the conciliation entry move to
        reconcile with the vendor bill and payment later."""
        result = []
        for sheet in self:
            employee_p = sheet.employee_id.sudo().work_contact_id
            company = sheet.company_id
            exp_intermediate_journal = (
                company.expense_intermediate_journal_id
                or company.expense_journal_id
                or sheet.journal_id
            )
            vendor_payable_move_lines = sheet._get_vendor_payable_move_lines()
            result.append(
                {
                    "company_id": company.id,
                    "journal_id": exp_intermediate_journal.id,
                    "ref": self.env._(
                        "%(expense_sheet_name)s | Expense conciliation",
                        expense_sheet_name=self.name,
                    ),
                    "narration": self.env._(
                        "Expense conciliation entry for "
                        "'%(expense_sheet_name)s' expense sheet "
                        "and taking in consideration '%(vendor_move_names)s' moves.",
                        expense_sheet_name=sheet.name,
                        vendor_move_names=", ".join(
                            vendor_payable_move_lines.mapped("move_id.name")
                        ),
                    ),
                    "move_type": "entry",
                    "date": sheet.accounting_date,
                    "currency_id": sheet.currency_id.id,
                    "expense_sheet_id": sheet.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": sheet.name,
                                "partner_id": employee_p.id,
                                "account_id": employee_p.property_account_payable_id.id,
                                "debit": 0.0,
                                "credit": sheet.amount_residual,
                            }
                        ),
                        *[
                            Command.create(
                                {
                                    "name": f"{payable_move_line.move_id.name} "
                                    f"({payable_move_line.move_id.ref})",
                                    "partner_id": payable_move_line.partner_id.id,
                                    "account_id": payable_move_line.account_id.id,
                                    "debit": -payable_move_line.amount_residual,
                                    "credit": 0.0,
                                }
                            )
                            for payable_move_line in vendor_payable_move_lines
                        ],
                    ],
                }
            )

        return result

    def _reconcile_conciliation_move_with_vendor_bills(self):
        """Reconcile the Conciliation Entry and the Vendor Bill."""
        for sheet in self:
            # Get the conciliation entry and post it if needed
            conciliation_move = sheet._get_conciliation_moves(posted=False)
            if not conciliation_move:
                continue
            if conciliation_move.state == "draft":
                conciliation_move.sudo().action_post()
            # Select the payable vendor lines to reconcile
            conciliation_vendor_payable_move_lines = (
                sheet._get_conciliation_payable_move_lines(for_employee=False)
            )
            vendor_payable_move_lines = sheet._get_vendor_payable_move_lines()
            lines_to_reconcile = (
                conciliation_vendor_payable_move_lines | vendor_payable_move_lines
            )
            lines_to_reconcile.reconcile()

    def _create_conciliation_moves(self):
        """Create an intermediate entry to reconcile with
        the vendor bills and payment later."""
        # Get the payable vendor bill lines to reconcile
        conciliation_moves = self._get_conciliation_moves(posted=True)
        for remaining_sheet in self - conciliation_moves.mapped("expense_sheet_id"):
            remaining_conciliation_move = (
                self.env["account.move"]
                .sudo()
                .create(remaining_sheet._prepare_conciliation_move_vals())
            )
            remaining_sheet._reconcile_conciliation_move_with_vendor_bills()
            conciliation_moves |= remaining_conciliation_move
        return conciliation_moves

    def action_register_payment(self):
        """Override to create the payment for the Conciliation entry to the Employee and
        create the conciliation entry if needed."""
        # Check if there are Vendor and Employee Bills at the same time
        employee_bills = self._get_vendor_moves(for_employee=True)
        vendor_bills = self._get_vendor_moves(for_employee=False)
        if vendor_bills and employee_bills:
            raise exceptions.UserError(
                self.env._(
                    "You cannot register a payments for Employees and Vendors "
                    "at the same time"
                )
            )
        # If payments are only for employee bills, use the normal flow
        if employee_bills:
            return super().action_register_payment()
        # At this point, we can assume that Vendor bills are not for the employee
        # Ensure all conciliation entries are created, posted and conciled
        conciliation_moves = self._get_conciliation_moves(posted=False)
        conciliation_moves.filtered(lambda move: move.state == "draft").mapped(
            "expense_sheet_id"
        )._reconcile_conciliation_move_with_vendor_bills()
        # Remaining sheets to process that are not in the conciliation moves
        sheets_to_create_conciliation_moves = self - conciliation_moves.mapped(
            "expense_sheet_id"
        )
        if sheets_to_create_conciliation_moves:
            conciliation_moves |= (
                sheets_to_create_conciliation_moves._create_conciliation_moves()
            )
        # All conciliation entries are created, so continue with the payment process
        # Choose company Expense Journal first, if not set, use the sheet Journal
        expense_journal = self.company_id.expense_journal_id or self.journal_id
        if len(expense_journal) > 1:
            raise exceptions.UserError(
                self.env._(
                    "You have multiple expense journals defined, please set a single "
                    "expense journal in the company settings to proceed with the "
                    "payment for Employees or pay one by one."
                )
            )
        # Check if all payments belongs to the same employee to set default bank account
        conciliation_emp_pay_move_lines = self._get_conciliation_payable_move_lines(
            for_employee=True
        )
        default_partner_bank_id = None
        if len(conciliation_emp_pay_move_lines.mapped("partner_id")) == 1:
            employee_partner = conciliation_emp_pay_move_lines.mapped("partner_id")[0]
            default_partner_bank_id = employee_partner.bank_ids[:1].id
        # Return the action to register payment for the conciliation entries
        # Group payment if all conciliation entries belongs to the same employee
        return conciliation_emp_pay_move_lines.action_register_payment(
            ctx={
                "default_partner_bank_id": default_partner_bank_id,
                "default_journal_id": expense_journal.id,
                "default_group_payment": bool(default_partner_bank_id),
            }
        )

    @api.depends("account_move_ids.line_ids.reconciled")
    def _compute_from_account_move_ids(self):
        res = super()._compute_from_account_move_ids()
        for sheet in self:
            # Only manage paid by Employee mode
            if sheet.payment_mode != "own_account":
                continue
            # If all bills belongs to the employee, we don't have nothing to do
            employee_bills = sheet._get_vendor_moves(for_employee=True)
            if employee_bills:
                continue
            # At this point, we can assume that Vendor bills are not for the employee
            # Check the payment status for the employee on the conciliation entry
            employee_conciliation_move_lines = (
                sheet._get_conciliation_payable_move_lines(for_employee=True)
            )
            if not employee_conciliation_move_lines:
                # No conciliation entry created yet or is not valid
                sheet.payment_state = "not_paid"
                sheet.amount_residual = sheet.total_amount
                continue

            if all(employee_conciliation_move_lines.mapped("reconciled")):
                sheet.payment_state = "paid"
                sheet.amount_residual = 0.0
            else:
                not_reconciled_lines = employee_conciliation_move_lines.filtered(
                    lambda line: not line.reconciled
                )
                sheet.amount_residual = -sum(
                    not_reconciled_lines.mapped("amount_residual")
                )
                if (
                    float_compare(
                        sheet.amount_residual,
                        -sum(not_reconciled_lines.mapped("balance")),
                        precision_rounding=sheet.currency_id.rounding,
                    )
                    == 0
                ):
                    sheet.payment_state = "not_paid"
                else:
                    sheet.payment_state = "partial"
        return res

    def _action_split_expenses(self):
        """Action to split expense sheet into multiple sheets
        with one expense line each."""
        result_sheets = self.env["hr.expense.sheet"].browse()
        for sheet in self:
            if sheet.state not in ("draft", "submit"):
                raise exceptions.UserError(
                    self.env._(
                        "Only expense sheets in 'To Submit' or 'Submitted' state "
                        "can be splitted. Expense Sheet '%s' is in state '%s'.",
                        sheet.name,
                        sheet.state,
                    )
                )
            if len(sheet.expense_line_ids) <= 1:
                result_sheets |= sheet
                continue
            for line in sheet.expense_line_ids:
                new_sheet = sheet.copy(default={"name": f"{sheet.name} - {line.name}"})
                new_sheet.message_post(
                    body=self.env._(
                        "This expense sheet has been created by splitting "
                        "the expense sheet '%s'.",
                        sheet.name,
                    )
                )
                line.sheet_id = new_sheet
                if sheet.state != "draft":  # Submitted
                    new_sheet._do_submit()
                result_sheets |= new_sheet
            try:
                sheet.sudo().unlink()
            except exceptions.UserError:
                # In case the user cannot unlink the sheet, refuse with a reason
                sheet._do_refuse(
                    self.env._(
                        "This expense sheet has been splitted into multiple sheets."
                    )
                )
        action = self.env["ir.actions.actions"]._for_xml_id(
            "hr_expense.action_hr_expense_sheet_all"
        )
        action.update(
            {
                "domain": [("id", "in", result_sheets.ids)],
                "name": self.env._("Splitted Expense Sheets"),
            }
        )
        return action
