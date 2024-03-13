# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        string="To Vendor",
        help="Paid by company direct to this vendor",
    )

    def _get_account_move_line_values(self):
        move_line_values_by_expense = super()._get_account_move_line_values()
        # If pay from company to vendor, change partner_id = vendor_id
        if move_line_values_by_expense:
            sheet = self[0].sheet_id
            payment_mode = sheet.payment_mode
            vendor_id = sheet.vendor_id.id
            if payment_mode == "company_account" and vendor_id:
                for expense_id, vals in move_line_values_by_expense.items():
                    expense = self.env["hr.expense"].browse(expense_id)
                    move_line_name = (
                        expense.vendor_id.name + ": " + expense.name.split("\n")[0][:64]
                    )
                    account_src = expense._get_expense_account_source()
                    account_dst = expense._get_expense_account_destination()
                    account_ids = [account_src.id, account_dst]
                    for val in vals:
                        val["partner_id"] = vendor_id
                        if val["account_id"] in account_ids:
                            val["name"] = move_line_name
        return move_line_values_by_expense

    def _get_expense_account_destination(self):
        self.ensure_one()
        if not (self.payment_mode == "company_account" and self.vendor_id):
            return super()._get_expense_account_destination()
        # Use vendor's account
        account_dest = (
            self.vendor_id.property_account_payable_id.id
            or self.vendor_id.parent_id.property_account_payable_id.id
        )
        return account_dest

    def _prepare_move_values(self):
        move_values = super()._prepare_move_values()
        if self.payment_mode == "company_account" and self.vendor_id:
            move_values["journal_id"] = self.sheet_id.journal_id.id
        return move_values


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    vendor_id = fields.Many2one(
        comodel_name="res.partner",
        related="expense_line_ids.vendor_id",
        string="To Vendor",
        readonly=True,
    )

    @api.constrains("expense_line_ids")
    def _check_payment_mode(self):
        res = super()._check_payment_mode()
        for sheet in self:
            expenses = sheet.expense_line_ids
            payment_mode = expenses.mapped("payment_mode")
            if payment_mode and payment_mode[0] == "company_account":
                if expenses and any(
                    expense.vendor_id != expenses[0].vendor_id for expense in expenses
                ):
                    raise ValidationError(
                        _("Expenses must be paying to the same vendor.")
                    )
        return res

    def paid_expense_sheets(self):
        """For expense paid direct to vendor, do not set done"""
        self = self.filtered(
            lambda l: l.payment_mode == "company_account" and not l.vendor_id
        )
        return super(HrExpenseSheet, self).paid_expense_sheets()

    def _update_sheets_pay_to_vendor(self):
        return self.write({"state": "post"})

    def action_sheet_move_create(self):
        # For expense paid by copany to vendor, only set state to post
        res = super().action_sheet_move_create()
        to_post = self.filtered(
            lambda l: l.payment_mode == "company_account" and l.vendor_id
        )
        to_post._update_sheets_pay_to_vendor()
        return res
