# Copyright 2019 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare


class AccountMove(models.Model):
    _inherit = "account.move"

    is_petty_cash = fields.Boolean(
        string="Petty Cash", readonly=True, states={"draft": [("readonly", False)]},
    )

    def action_post(self):
        self._check_petty_cash_amount()
        return super().action_post()

    @api.constrains("invoice_line_ids", "line_ids")
    def _check_petty_cash_amount(self):
        petty_cash_env = self.env["petty.cash"]
        for rec in self:
            petty_cash = petty_cash_env.search(
                [("partner_id", "=", rec.partner_id.id)], limit=1
            )
            if petty_cash and rec.invoice_line_ids:
                account = petty_cash.account_id
                # Must check Petty Cash on vender bills
                if (
                    not rec.is_petty_cash
                    and account.id in rec.invoice_line_ids.mapped("account_id").ids
                ):
                    raise UserError(
                        _("Please check Petty Cash on {}.".format(rec.display_name))
                    )
                if rec.is_petty_cash:
                    if len(rec.invoice_line_ids) > 1:
                        raise UserError(
                            _(
                                "{} with petty cash checked must contain "
                                "only 1 line.".format(rec.display_name)
                            )
                        )
                    if rec.invoice_line_ids.account_id.id != account.id:
                        raise UserError(
                            _(
                                "Account on invoice line should be {}.".format(
                                    account.display_name
                                )
                            )
                        )
                    balance = petty_cash.petty_cash_balance
                    limit = petty_cash.petty_cash_limit
                    max_amount = limit - balance
                    amount = sum(
                        rec.invoice_line_ids.filtered(
                            lambda l: l.account_id == account
                        ).mapped("price_subtotal")
                    )
                    company_currency = rec.company_id.currency_id
                    amount_company = rec.currency_id._convert(
                        amount,
                        company_currency,
                        rec.company_id,
                        rec.date or fields.Date.today(),
                    )
                    prec = rec.currency_id.rounding
                    if (
                        float_compare(
                            amount_company, max_amount, precision_rounding=prec
                        )
                        == 1
                    ):
                        raise ValidationError(
                            _(
                                "Petty Cash balance is %s %s.\n"
                                "Max amount to add is %s %s."
                            )
                            % (
                                "{:,.2f}".format(balance),
                                company_currency.symbol,
                                "{:,.2f}".format(max_amount),
                                company_currency.symbol,
                            )
                        )

    def _add_petty_cash_invoice_line(self, petty_cash):
        self.ensure_one()
        # Get suggested currency amount
        amount = petty_cash.petty_cash_limit - petty_cash.petty_cash_balance
        company_currency = self.env.user.company_id.currency_id
        amount_doc_currency = company_currency._convert(
            amount, self.currency_id, self.company_id, self.date or fields.Date.today(),
        )

        inv_line = self.env["account.move.line"].new(
            {
                "name": petty_cash.account_id.name,
                "account_id": petty_cash.account_id.id,
                "partner_id": petty_cash.partner_id.id,
                "price_unit": amount_doc_currency,
                "quantity": 1,
            }
        )
        return inv_line

    @api.onchange("is_petty_cash", "partner_id")
    def _onchange_is_petty_cash(self):
        self.line_ids = False
        self.invoice_line_ids = False
        ctx = self._context.copy()
        if self.is_petty_cash:
            if not self.partner_id:
                raise ValidationError(_("Please select petty cash holder"))
            # Selected parenter must be petty cash holder
            petty_cash = self.env["petty.cash"].search(
                [("partner_id", "=", self.partner_id.id)], limit=1
            )
            if not petty_cash:
                raise ValidationError(
                    _("%s is not a petty cash holder") % self.partner_id.name
                )
            self.invoice_line_ids = self._add_petty_cash_invoice_line(petty_cash)
            if petty_cash.journal_id:
                ctx.update(
                    {
                        "default_journal_id": petty_cash.journal_id.id,
                        "default_type": "general",
                    }
                )
        self.journal_id = self.with_context(ctx)._get_default_journal()
