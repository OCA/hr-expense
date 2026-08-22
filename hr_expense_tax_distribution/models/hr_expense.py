# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    tax_line_ids = fields.One2many(
        comodel_name="hr.expense.tax.line",
        inverse_name="expense_id",
        string="Tax Distribution Lines",
        copy=True,
    )
    has_tax_distribution = fields.Boolean(
        compute="_compute_has_tax_distribution",
        store=True,
    )
    # Disable precompute on these fields because they depend on the One2many
    # relation tax_line_ids, which cannot be precomputed.
    tax_amount_currency = fields.Monetary(precompute=False)
    untaxed_amount_currency = fields.Monetary(precompute=False)
    tax_amount = fields.Monetary(precompute=False)
    untaxed_amount = fields.Monetary(precompute=False)

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends("tax_line_ids", "tax_line_ids.base_amount_currency")
    def _compute_has_tax_distribution(self):
        for expense in self:
            expense.has_tax_distribution = bool(expense.tax_line_ids)

    # -------------------------------------------------------------------------
    # Onchange
    # -------------------------------------------------------------------------

    @api.onchange("tax_ids")
    def _onchange_tax_ids_generate_distribution_lines(self):
        """Keep one distribution line per tax; clear them for single-tax expenses."""
        if len(self.tax_ids) <= 1:
            self.tax_line_ids = [Command.clear()]
            return
        self.tax_line_ids = self._sync_tax_distribution_lines(self.tax_ids)

    def _sync_tax_distribution_lines(self, taxes):
        """Return ORM Commands syncing the distribution lines with ``taxes``:
        keep existing single-tax lines, drop removed ones, create the new ones.
        Split out so downstream modules can add extra fields on created lines.
        """
        self.ensure_one()
        # _origin gives us real DB records (ids are plain ints).
        # On a new expense, _origin.tax_line_ids is empty — that is correct.
        existing_by_tax_id = {
            line.tax_ids.ids[0]: line
            for line in self.tax_line_ids
            if len(line.tax_ids) == 1
        }
        current_tax_ids = set(taxes.ids)

        commands = []
        covered = set()

        # Keep existing single-tax lines whose tax is still selected.
        for tax_id, line in existing_by_tax_id.items():
            if tax_id in current_tax_ids:
                commands.append(Command.link(line.id))
            else:
                commands.append(Command.delete(line.id))
            covered.add(tax_id)

        # Create new lines for taxes not yet covered.
        for tax in taxes._origin.filtered(lambda t: t.id not in covered):
            commands.append(
                Command.create(
                    {
                        "tax_ids": [Command.set(tax.ids)],
                        "base_amount_currency": 0.0,
                    }
                )
            )

        return commands

    @api.depends(
        "total_amount_currency",
        "tax_ids",
        "tax_line_ids.tax_amount_currency",
        "tax_line_ids.total_amount_currency",
    )
    def _compute_tax_amount_currency(self):
        """Derive amounts from the distribution lines when set, else super()."""
        dist_expenses = self.filtered(
            lambda he: he.has_tax_distribution
            and any(dl.base_amount_currency for dl in he.tax_line_ids)
        )
        for expense in dist_expenses:
            tax_sum = sum(expense.tax_line_ids.mapped("tax_amount_currency"))
            expense.tax_amount_currency = tax_sum
            expense.untaxed_amount_currency = expense.total_amount_currency - tax_sum
        return super(HrExpense, self - dist_expenses)._compute_tax_amount_currency()

    @api.depends(
        "total_amount",
        "currency_rate",
        "tax_ids",
        "is_multiple_currency",
        "tax_line_ids.tax_amount_currency",
    )
    def _compute_tax_amount(self):
        """Derive tax_amount (company currency) from the distribution lines when set."""
        dist_expenses = self.filtered(
            lambda he: he.has_tax_distribution
            and any(dl.base_amount_currency for dl in he.tax_line_ids)
        )
        for expense in dist_expenses:
            if expense.is_multiple_currency:
                tax_sum_currency = sum(
                    expense.tax_line_ids.mapped("tax_amount_currency")
                )
                expense.tax_amount = expense.currency_id._convert(
                    tax_sum_currency,
                    expense.company_currency_id,
                    expense.company_id,
                    expense.date or fields.Date.context_today(expense),
                )
            else:
                expense.tax_amount = sum(
                    expense.tax_line_ids.mapped("tax_amount_currency")
                )
        return super(HrExpense, self - dist_expenses)._compute_tax_amount()

    def _check_tax_distribution_total(self):
        """Validate that the distribution line totals match the expense total.

        Called from action_submit rather than via @api.constrains so onchange
        does not fail while lines are still being filled in.
        """
        for expense in self:
            if not expense.tax_line_ids:
                continue
            if not expense.total_amount_currency:
                continue
            if any(
                expense.currency_id.is_zero(tl.base_amount_currency)
                for tl in expense.tax_line_ids
            ):
                raise ValidationError(
                    expense.env._(
                        'Expense "%(name)s" has tax distribution lines with a '
                        "zero base amount. Please fill in all base amounts before "
                        "submitting.",
                        name=expense.name,
                    )
                )
            distributed_total = sum(
                expense.tax_line_ids.mapped("total_amount_currency")
            )
            diff = abs(distributed_total - expense.total_amount_currency)
            # Use the currency rounding to allow for floating-point drift
            if not expense.currency_id.is_zero(diff):
                raise ValidationError(
                    expense.env._(
                        "The sum of tax distribution line totals (%(distributed)s) "
                        "does not match the expense total amount (%(total)s) on "
                        'expense "%(name)s". '
                        "Please adjust the base amounts so that the totals match.",
                        distributed=expense.currency_id.format(distributed_total),
                        total=expense.currency_id.format(expense.total_amount_currency),
                        name=expense.name,
                    )
                )

    def action_submit(self):
        """Validate tax distribution totals before submission."""
        self._check_tax_distribution_total()
        return super().action_submit()

    # -------------------------------------------------------------------------
    # Accounting entry generation
    # -------------------------------------------------------------------------

    def _get_tax_distribution_move_lines_vals(self):
        """One account.move.line vals dict per distribution line.

        own_account only: that move is an ``in_receipt``, so price_unit (TTC)
        drives the tax recompute. ``_prepare_payments_vals`` posts an ``entry``
        and computes the amounts itself.
        """
        self.ensure_one()
        move_lines = []
        account_src = self._get_base_account()
        partner_id = (
            False
            if self.payment_mode == "company_account"
            else self.employee_id.sudo().work_contact_id.id
        )
        quantity = self.quantity if self.product_has_cost and self.quantity else 1.0

        for dist_line in self.tax_line_ids:
            price_unit = dist_line.total_amount_currency / quantity if quantity else 0.0
            move_lines.append(
                {
                    "name": self._get_move_line_name(),
                    "account_id": account_src.id,
                    "product_id": self.product_id.id,
                    "product_uom_id": self.product_uom_id.id,
                    "analytic_distribution": self.analytic_distribution,
                    "expense_id": self.id,
                    "tax_ids": [Command.set(dist_line.tax_ids.ids)],
                    "price_unit": price_unit,
                    "quantity": quantity,
                    "currency_id": self.currency_id.id,
                    "partner_id": partner_id,
                }
            )

        return move_lines

    def _prepare_payments_vals(self):
        """Override for the 'company_account' flow.

        The move is an ``entry``: lines take ``balance`` verbatim and
        ``tax_ids`` is never expanded, so mirror core's tax computation with
        one base line per distribution line.
        """
        if not self.has_tax_distribution:
            return super()._prepare_payments_vals()

        self.ensure_one()
        journal = self.journal_id
        payment_method_line = self.payment_method_line_id
        if not payment_method_line:
            raise ValidationError(
                self.env._(
                    "You need to add a manual payment method on the journal (%s)",
                    journal.name,
                )
            )

        AccountTax = self.env["account.tax"]
        rate = (
            abs(self.total_amount_currency / self.total_amount)
            if self.total_amount
            else 0.0
        )
        account_src = self._get_base_account()
        # price_unit is tax-included: the wrapper passes special_mode='total_included'.
        base_lines = [
            self._prepare_base_line_for_taxes_computation(
                price_unit=dist_line.total_amount_currency,
                quantity=1.0,
                account_id=account_src,
                rate=rate,
                tax_ids=dist_line.tax_ids,
            )
            for dist_line in self.tax_line_ids
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines, self.company_id, include_caba_tags=True
        )
        tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id)

        move_lines = []
        base_move_lines = []
        for base_line, to_update in tax_results["base_lines_to_update"]:
            base_move_line = {
                "name": self._get_move_line_name(),
                "account_id": base_line["account_id"].id,
                "product_id": base_line["product_id"].id,
                "analytic_distribution": base_line["analytic_distribution"],
                "expense_id": self.id,
                "tax_ids": [Command.set(base_line["tax_ids"].ids)],
                "tax_tag_ids": to_update["tax_tag_ids"],
                "amount_currency": to_update["amount_currency"],
                "balance": to_update["balance"],
                "currency_id": base_line["currency_id"].id,
                "partner_id": self.vendor_id.id,
            }
            move_lines.append(base_move_line)
            base_move_lines.append(base_move_line)

        total_tax_line_balance = 0.0
        for tax_line in tax_results["tax_lines_to_add"]:
            total_tax_line_balance += tax_line["balance"]
            move_lines.append(tax_line)

        # Core has one base line; with several, absorb the residue into the last.
        if base_move_lines:
            expected_base_balance = self.total_amount - total_tax_line_balance
            residue = expected_base_balance - sum(
                line["balance"] for line in base_move_lines
            )
            base_move_lines[-1]["balance"] += residue

        # Outstanding payment line.
        move_lines.append(
            {
                "name": self._get_move_line_name(),
                "account_id": self._get_expense_account_destination(),
                "balance": -self.total_amount,
                "amount_currency": self.currency_id.round(-self.total_amount_currency),
                "currency_id": self.currency_id.id,
                "partner_id": self.vendor_id.id,
            }
        )

        payment_vals = {
            "date": self.date,
            "memo": self.name,
            "journal_id": journal.id,
            "amount": self.total_amount_currency,
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.vendor_id.id,
            "currency_id": self.currency_id.id,
            "payment_method_line_id": payment_method_line.id,
            "company_id": self.company_id.id,
        }
        move_vals = {
            **self._prepare_move_vals(),
            "ref": self.name,
            "date": self.date,
            "journal_id": journal.id,
            "partner_id": self.vendor_id.id,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "line_ids": [Command.create(line) for line in move_lines],
            "attachment_ids": [
                Command.create(
                    attachment.copy_data(
                        {
                            "res_model": "account.move",
                            "res_id": False,
                            "raw": attachment.raw,
                        }
                    )[0]
                )
                for attachment in self.attachment_ids
            ],
        }
        return move_vals, payment_vals

    def _prepare_receipts_vals(self):
        """Override for the 'own_account' flow."""
        if not any(exp.has_tax_distribution for exp in self):
            return super()._prepare_receipts_vals()

        return_vals = []
        for employee_sudo, expenses_sudo in self.sudo().grouped("employee_id").items():
            attachments_data = [
                Command.create(
                    attachment.copy_data(
                        {
                            "res_model": "account.move",
                            "res_id": False,
                            "raw": attachment.raw,
                        }
                    )[0]
                )
                for attachment in expenses_sudo.attachment_ids
            ]
            multiple_expenses_name = self.env._(
                "Expenses of %(employee)s", employee=employee_sudo.name
            )
            move_ref = (
                expenses_sudo.name
                if len(expenses_sudo) == 1
                else multiple_expenses_name
            )

            line_ids = []
            for expense_sudo in expenses_sudo:
                if expense_sudo.has_tax_distribution:
                    vals = expense_sudo._get_tax_distribution_move_lines_vals()
                    line_ids.extend([Command.create(line) for line in vals])
                else:
                    line_ids.append(
                        Command.create(expense_sudo._prepare_move_lines_vals())
                    )

            return_vals.append(
                {
                    **expenses_sudo._prepare_move_vals(),
                    "ref": move_ref,
                    "move_type": "in_receipt",
                    "partner_id": employee_sudo.work_contact_id.id,
                    "commercial_partner_id": employee_sudo.user_partner_id.id,
                    "currency_id": expenses_sudo.company_currency_id.id,
                    "company_id": expenses_sudo.company_id.id,
                    "line_ids": line_ids,
                    "partner_bank_id": employee_sudo.primary_bank_account_id.id,
                    "attachment_ids": attachments_data,
                }
            )
        return return_vals
