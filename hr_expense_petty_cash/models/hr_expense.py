# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    payment_mode = fields.Selection(selection_add=[("petty_cash", "Petty Cash")])
    petty_cash_id = fields.Many2one(
        string="Petty cash holder",
        comodel_name="petty.cash",
        ondelete="restrict",
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def _prepare_expense_vals(self):
        vals = {
            "company_id": self.company_id.id,
            "employee_id": self[0].employee_id.id,
            "name": self[0].name if len(self) == 1 else "",
            "expense_line_ids": [(6, 0, self.ids)],
        }
        return vals

    def _create_sheet_from_expense_petty_cash(self):
        """ Overwrite function _create_sheet_from_expenses(), if petty cash mode. """
        if any(expense.state != "draft" or expense.sheet_id for expense in self):
            raise UserError(_("You cannot report twice the same line!"))
        if len(self.mapped("employee_id")) != 1:
            raise UserError(
                _(
                    "You cannot report expenses for different "
                    "employees in the same report."
                )
            )
        if any(not expense.product_id for expense in self):
            raise UserError(_("You can not create report without product."))
        ctx = self._context.copy()
        ctx.update({"default_petty_cash_id": self[0].petty_cash_id.id})
        sheet = (
            self.env["hr.expense.sheet"]
            .with_context(ctx)
            .create(self._prepare_expense_vals())
        )
        sheet._onchange_employee_id()
        return sheet

    def _create_sheet_from_expenses(self):
        payment_mode = set(self.mapped("payment_mode"))
        if len(payment_mode) > 1 and "petty_cash" in payment_mode:
            raise UserError(
                _("You cannot create report from many petty cash mode and other.")
            )
        if all(expense.payment_mode == "petty_cash" for expense in self):
            return self._create_sheet_from_expense_petty_cash()
        return super()._create_sheet_from_expenses()

    def _get_account_move_line_values(self):
        res = super()._get_account_move_line_values()
        for expense in self.filtered(lambda p: p.payment_mode == "petty_cash"):
            line = res[expense.id][1]
            line["account_id"] = expense.petty_cash_id.account_id.id
            line["partner_id"] = expense.petty_cash_id.partner_id.id
            res[expense.id][1] = line
        return res
