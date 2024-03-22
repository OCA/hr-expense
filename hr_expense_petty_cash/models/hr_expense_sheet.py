# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.tools.misc import clean_context


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    petty_cash_id = fields.Many2one(
        string="Petty cash holder",
        comodel_name="petty.cash",
        ondelete="restrict",
        compute="_compute_petty_cash",
        store=True,
    )

    @api.depends("expense_line_ids", "payment_mode")
    def _compute_petty_cash(self):
        for rec in self:
            rec.petty_cash_id = False
            if rec.payment_mode == "petty_cash":
                set_petty_cash_ids = set()
                for line in rec.expense_line_ids:
                    set_petty_cash_ids.add(line.petty_cash_id.id)
                if len(set_petty_cash_ids) == 1:
                    rec.petty_cash_id = rec.env["petty.cash"].browse(
                        set_petty_cash_ids.pop()
                    )
                    journal_petty_cash = rec.petty_cash_id.journal_id
                    if journal_petty_cash:
                        rec.journal_id = journal_petty_cash
                else:
                    raise ValidationError(
                        _("You cannot create report from many petty cash holders.")
                    )

    @api.constrains("expense_line_ids", "total_amount")
    def _check_petty_cash_amount(self):
        for rec in self:
            if rec.payment_mode == "petty_cash":
                petty_cash = rec.petty_cash_id
                balance = petty_cash.petty_cash_balance
                amount = rec.total_amount
                company_currency = rec.company_id.currency_id
                amount_company = rec.currency_id._convert(
                    amount,
                    company_currency,
                    rec.company_id,
                    rec.accounting_date or fields.Date.today(),
                )
                prec = rec.currency_id.rounding
                if float_compare(amount_company, balance, precision_rounding=prec) == 1:
                    raise ValidationError(
                        _(
                            "Not enough money in petty cash holder.\n"
                            "You are requesting {amount_company}{symbol}, "
                            "but the balance is {balance}{symbol}."
                        ).format(
                            amount_company="{:,.2f}".format(amount_company),
                            symbol=company_currency.symbol,
                            balance="{:,.2f}".format(balance),
                        )
                    )

    def _do_create_moves(self):
        petty_cash_account_sheets = self.filtered(
            lambda sheet: sheet.payment_mode == "petty_cash"
        )
        self_without_petty_cash = self - petty_cash_account_sheets
        if petty_cash_account_sheets:
            self = self.with_context(
                **clean_context(self.env.context)
            )  # remove default_*
            moves = self.env["account.move"].create(
                [sheet._prepare_bill_vals() for sheet in petty_cash_account_sheets]
            )
            moves.action_post()
            self.activity_update()
            return moves
        return super(HrExpenseSheet, self_without_petty_cash)._do_create_moves()

    def action_open_account_move(self):
        self.ensure_one()
        if self.payment_mode == "petty_cash":
            return {
                "name": self.account_move_id.name,
                "type": "ir.actions.act_window",
                "view_mode": "form",
                "views": [[False, "form"]],
                "res_model": "account.move",
                "res_id": self.account_move_id.id,
            }
        return super().action_open_account_move()

    def _get_petty_cash_move_line_vals(self):
        self.ensure_one()
        move_line_vals = []
        for expense in self.expense_line_ids:
            move_line_name = (
                expense.employee_id.name + ": " + expense.name.split("\n")[0][:64]
            )
            partner_id = (
                expense.employee_id.sudo().address_home_id.commercial_partner_id.id
            )
            # source move line
            move_line_src = expense._get_petty_cash_move_line(
                move_line_name,
                partner_id,
                expense.total_amount_company,
                expense.total_amount,
            )
            move_line_values = [move_line_src]

            # destination move line
            move_line_dst = expense._get_petty_cash_move_line(
                move_line_name,
                expense.petty_cash_id.partner_id.id,
                -expense.total_amount_company,
                -expense.total_amount,
                expense.petty_cash_id.account_id,
            )
            move_line_values.append(move_line_dst)
            move_line_vals.extend(move_line_values)
        return move_line_vals

    def _prepare_bill_vals(self):
        """create journal entry instead of bills when clearing document"""
        self.ensure_one()
        res = super()._prepare_bill_vals()
        if self.payment_mode == "petty_cash":
            res["move_type"] = "entry"
            move_line_vals = self._get_petty_cash_move_line_vals()
            res["line_ids"] = [Command.create(x) for x in move_line_vals]
        return res

    def action_sheet_move_create(self):
        res = super().action_sheet_move_create()
        paid_petty_cash = self.filtered(lambda m: m.payment_mode == "petty_cash")
        paid_petty_cash.write(
            {"state": "done", "amount_residual": 0.0, "payment_state": "paid"}
        )
        return res
