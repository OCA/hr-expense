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
    # Disable precompute on these three fields: our _compute overrides depend
    # on hr.expense.tax.line.tax_amount_currency which is not precomputable
    # itself (it lives on a new model).  Keeping precompute=True would trigger
    # an Odoo UserWarning at startup and silently break the precompute chain.
    tax_amount_currency = fields.Monetary(precompute=False)
    untaxed_amount_currency = fields.Monetary(precompute=False)
    tax_amount = fields.Monetary(precompute=False)

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
        """Maintain tax distribution lines in sync with tax_ids.

        Rules:
        - If tax_ids has 0 or 1 tax: clear all distribution lines (single-tax
          expenses use the standard Odoo flow; no distribution needed).
        - If tax_ids has 2+ taxes: one line per tax is maintained.
          Existing lines whose tax is still present are preserved (base amounts
          are kept).  Lines for removed taxes are deleted.  Lines for newly
          added taxes are created with base_amount_currency = 0.
        """
        if len(self.tax_ids) <= 1:
            self.tax_line_ids = [Command.clear()]
            return
        self.tax_line_ids = self._sync_tax_distribution_lines(self.tax_ids)

    def _sync_tax_distribution_lines(self, taxes):
        """Return a list of ORM Commands to sync tax distribution lines with
        the given ``taxes`` recordset.

        Lines covering a single tax still present in ``taxes`` are preserved
        via Command.link() so their base_amount_currency is kept.  Lines for
        taxes that have been removed are dropped.  A new Command.create() is
        added for each tax not yet covered by a single-tax line.

        The caller is responsible for assigning the result to ``tax_line_ids``
        (onchange) or passing it to write() / create() (tests, other callers).
        This design allows downstream modules to override this method and add
        extra fields (e.g. an account_id) to the created lines.

        Uses self._origin.tax_line_ids so that ids are always real DB integers,
        even when called from inside an onchange where self is a virtual record.
        On a new (unsaved) expense, _origin.tax_line_ids is an empty recordset,
        which is the correct starting point.
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
        """When distribution lines exist *and* have non-zero amounts, derive
        tax_amount_currency and untaxed_amount_currency from their sum.
        Falls back to super() otherwise (standard Odoo behavior)."""
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
        """When distribution lines exist *and* have non-zero amounts, derive
        tax_amount (company currency) from the distribution line sums."""
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
        """Validate that distribution line totals match the expense total.

        Called explicitly from action_submit_expenses instead of via
        @api.constrains, to avoid false positives during onchange when lines
        are being built incrementally (some lines may still be at zero).
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
        """Build account.move.line value dicts for one expense when tax
        distribution lines are defined.

        Reusable by both the 'own_account' (vendor bill) and 'company_account'
        (direct payment) flows.  The caller is responsible for appending the
        balancing destination line.

        ``price_unit`` is set to ``total_amount_currency / quantity`` (TTC) so
        that Odoo's invoice recompute extracts the base amount and the tax
        amount correctly, mirroring the behaviour of the standard
        ``_prepare_move_lines_vals`` which passes ``self.price_unit`` (also TTC
        for expenses).  ``quantity`` is taken from the parent expense when the
        product has a cost (``product_has_cost`` is True), falling back to 1.0
        otherwise.
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
        """Override for the 'company_account' flow."""
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

        move_lines = self._get_tax_distribution_move_lines_vals()
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
