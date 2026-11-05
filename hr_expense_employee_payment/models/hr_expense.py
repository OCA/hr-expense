# Copyright 2025 Moduon Team S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0)

from odoo import Command, api, fields, models
from odoo.tools import float_is_zero


class HrExpense(models.Model):
    _inherit = "hr.expense"

    conciliation_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Conciliation Entry",
        help="Intermediate entry created to reconcile with the vendor "
        "bill and payment later.",
    )

    @api.model
    def _get_vendor_moves_domain(self):
        """Return the domain to get the vendor moves linked to the expense."""
        return fields.Domain("move_type", "=", "in_invoice")

    def _get_vendor_move(self):
        """Get the vendor move linked to the expense."""
        vendor_moves = self.env["account.move"].browse()
        vendor_moves_domain = self._get_vendor_moves_domain()
        for expense in self:
            if expense.account_move_id.filtered_domain(vendor_moves_domain):
                vendor_moves |= expense.account_move_id
        return vendor_moves

    def _get_vendor_payable_move_lines(self):
        """Get the payable move lines from the vendor bills linked to
        selected expense sheets that has *something to be paid*."""
        return self._get_vendor_move().line_ids.filtered(
            lambda line: line.display_type == "payment_term"
            and not float_is_zero(
                line.amount_residual, precision_rounding=line.currency_id.rounding
            )
        )

    def _prepare_conciliation_move_vals(self):
        """Prepare the values for the conciliation entry move to
        reconcile with the vendor bill and payment later."""
        result = []
        for expense in self:
            employee_p = expense.employee_id.sudo().work_contact_id
            company = expense.company_id
            exp_intermediate_journal = (
                company.expense_intermediate_journal_id
                or company.expense_journal_id
                or expense.journal_id
            )
            vendor_payable_move_lines = expense._get_vendor_payable_move_lines()
            vendor_date = vendor_payable_move_lines.move_id[:1].date
            result.append(
                {
                    "company_id": company.id,
                    "journal_id": exp_intermediate_journal.id,
                    "ref": self.env._(
                        "%(expense_name)s | Expense conciliation",
                        expense_name=expense.name,
                    ),
                    "narration": self.env._(
                        "Expense conciliation entry for "
                        "'%(expense_name)s' expense "
                        "and taking in consideration '%(vendor_move_names)s' moves.",
                        expense_name=expense.name,
                        vendor_move_names=", ".join(
                            vendor_payable_move_lines.mapped("move_id.name")
                        ),
                    ),
                    "move_type": "entry",
                    "date": vendor_date,
                    "currency_id": expense.currency_id.id,
                    "line_ids": [
                        Command.create(
                            {
                                "name": expense.name,
                                "partner_id": employee_p.id,
                                "account_id": employee_p.property_account_payable_id.id,
                                "debit": 0.0,
                                "credit": expense.amount_residual,
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

    def _get_conciliation_payable_move_lines(self, for_employee=False):
        """Obtain the posted payable move lines from the conciliation entries
        for selected expense sheets.

        :param for_employee: True: Lines for the employee. False: Lines for the vendor.
        :return: A recordset of account.move.line matching conciliation payable lines.
        """
        conciliation_payable_lines = self.env["account.move.line"].browse()
        for expense in self.filtered("conciliation_move_id"):
            if for_employee:
                partner = expense.employee_id.sudo().work_contact_id  # Employee
            else:
                partner = expense._get_vendor_move().partner_id  # Vendor
            amount_field = "credit" if for_employee else "debit"
            conciliation_payable_lines |= (
                expense.conciliation_move_id.line_ids.filtered_domain(
                    [
                        ("partner_id", "=", partner.id),
                        (amount_field, ">", 0.0),
                    ]
                )
            )
        return conciliation_payable_lines

    def _reconcile_conciliation_move_with_vendor_bills(self):
        """Reconcile the Conciliation Entry and the Vendor Bill."""
        for expense in self.filtered("conciliation_move_id"):
            if expense.conciliation_move_id.state == "draft":
                expense.conciliation_move_id.sudo().action_post()
            # Select the Vendor lines to reconcile
            conciliation_vendor_payable_move_lines = (
                expense._get_conciliation_payable_move_lines(for_employee=False)
            )
            vendor_payable_move_lines = expense._get_vendor_payable_move_lines()
            # Check Vendor Bills that needs to be reconciled
            if conciliation_vendor_payable_move_lines and vendor_payable_move_lines:
                lines_to_reconcile = (
                    conciliation_vendor_payable_move_lines | vendor_payable_move_lines
                )
                lines_to_reconcile.reconcile()

    def _create_conciliation_moves(self, auto_reconcile=True):
        """Create an intermediate entry to reconcile with the vendor bills
        and payment later.

        :param auto_reconcile: Automatically reconcile the conciliation moves
        with the vendor bills.
        :return: A recordset of account.move with the created conciliation moves.
        """
        conciliation_moves = self.env["account.move"].browse()
        for expense in self:
            if not expense.conciliation_move_id:
                expense.conciliation_move_id = (
                    self.env["account.move"]
                    .sudo()
                    .create(expense._prepare_conciliation_move_vals())
                )
            conciliation_moves |= expense.conciliation_move_id
        if auto_reconcile:
            self._reconcile_conciliation_move_with_vendor_bills()
        return conciliation_moves

    def action_open_conciliation_move(self):
        """Open the conciliation entry created for the expense."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "name": self.conciliation_move_id.name,
            "view_mode": "form",
            "res_id": self.conciliation_move_id.id,
            "views": [(False, "form")],
        }

    @api.depends("conciliation_move_id.line_ids.reconciled")
    def _compute_state(self):
        res = super()._compute_state()
        for expense in self:
            if not expense.conciliation_move_id or not expense.account_move_id:
                continue
            conciliation_employee_payable_move_lines = (
                expense._get_conciliation_payable_move_lines(
                    for_employee=True,
                )
            )
            if all(conciliation_employee_payable_move_lines.mapped("reconciled")):
                expense.state = "paid"
            else:
                # Conciliation entry exists but is not fully paid
                expense.state = "in_payment"
        return res

    def action_pay_employee(self):
        """Register employee payment"""
        conciliation_employee_payable_move_lines = (
            self._get_conciliation_payable_move_lines(for_employee=True)
        )
        return conciliation_employee_payable_move_lines.action_register_payment()
