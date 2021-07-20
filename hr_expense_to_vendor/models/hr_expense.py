# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    partner_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_partner_id",
        string="Vendor",
        store=True,
        required=True,
        readonly=False,
        states={"approved": [("readonly", True)], "done": [("readonly", True)]},
        check_company=True,
        tracking=True,
    )

    @api.depends("employee_id")
    def _compute_partner_id(self):
        for expense in self:
            expense.partner_id = False or expense.employee_id.address_home_id

    def _get_expense_account_dest_vendor(self):
        self.ensure_one()
        account_dest = self.env["account.account"]
        partner = self.partner_id
        account_dest = (
            partner.property_account_payable_id.id
            or partner.parent_id.property_account_payable_id.id
        )
        return account_dest

    def _get_expense_account_destination(self):
        """ Add account value from partner_id """
        self.ensure_one()
        if self.payment_mode != "company_account":
            return self._get_expense_account_dest_vendor()
        return super()._get_expense_account_destination()

    def _get_account_move_line_values(self):
        """ Get partner_id from expense """
        move_line_values_by_expense = super()._get_account_move_line_values()
        for expense in self:
            for ml_value in move_line_values_by_expense[expense.id]:
                ml_value["partner_id"] = expense.partner_id.id
        return move_line_values_by_expense
