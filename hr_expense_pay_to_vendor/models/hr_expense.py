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

    def action_sheet_move_create(self):
        # For expense paid by copany to vendor, only set state to post
        res = super().action_sheet_move_create()
        to_post = self.filtered(
            lambda l: l.payment_mode == "company_account" and l.vendor_id
        )
        to_post.write({"state": "post"})
        return res

    def _prepare_payment_vals(self):
        self.ensure_one()
        payment_vals = super()._prepare_payment_vals()
        if self.payment_mode == "company_account" and self.vendor_id:
            for line in payment_vals["line_ids"]:
                line[2]["partner_id"] = self.vendor_id.id
                # Overwrite name without taxes
                if line[2].get("tax_base_amount", False):
                    continue
                expense_name = line[2]["name"].split(":")[1].strip()
                line[2]["name"] = f"{self.vendor_id.name}: {expense_name}"
        return payment_vals
