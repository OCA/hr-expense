# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.misc import format_date


class HrExpense(models.Model):
    _inherit = "hr.expense"

    payment_mode = fields.Selection(selection_add=[("petty_cash", "Petty Cash")])
    petty_cash_id = fields.Many2one(
        string="Petty cash holder",
        comodel_name="petty.cash",
        ondelete="restrict",
        check_company=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    def _get_account_move_line_values(self):
        res = super()._get_account_move_line_values()
        for expense in self.filtered(lambda p: p.payment_mode == "petty_cash"):
            line = res[expense.id][-1]
            line["account_id"] = expense.petty_cash_id.account_id.id
            line["partner_id"] = expense.petty_cash_id.partner_id.id
            res[expense.id][-1] = line
        return res

    def _get_default_expense_sheet_values(self):
        """Core Odoo filter own_account and company only.
        this function overwrite for petty cash"""
        petty_cash = self.filtered(lambda x: x.payment_mode == "petty_cash")
        todo = self - petty_cash
        if petty_cash:
            if any(expense.state != "draft" or expense.sheet_id for expense in self):
                raise UserError(_("You cannot report twice the same line!"))
            if len(self.mapped("employee_id")) != 1:
                raise UserError(
                    _(
                        "You cannot report expenses for different employees in the same report."
                    )
                )
            if any(not expense.product_id for expense in self):
                raise UserError(_("You can not create report without category."))
            if len(petty_cash) == 1:
                expense_name = petty_cash.name
            else:
                dates = petty_cash.mapped("date")
                min_date = format_date(self.env, min(dates))
                max_date = format_date(self.env, max(dates))
                expense_name = (
                    min_date
                    if max_date == min_date
                    else "%s - %s" % (min_date, max_date)
                )
            # check expense petty cash can't create holder more than 1
            if len(petty_cash.petty_cash_id) != 1:
                raise ValidationError(
                    _("You cannot create report from many petty cash holders.")
                )
            values = {
                "default_company_id": self.company_id.id,
                "default_employee_id": self[0].employee_id.id,
                "default_name": expense_name,
                "default_expense_line_ids": [Command.set(petty_cash.ids)],
                "default_state": "draft",
                "create": False,
            }
            # default journal from petty cash (if any)
            journal_petty_cash = self[0].petty_cash_id.journal_id
            if journal_petty_cash:
                values["default_journal_id"] = journal_petty_cash.id
            return values
        return super(HrExpense, todo)._get_default_expense_sheet_values()
