# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, _, api, fields, models
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
        "has_tax_distribution",
        "tax_line_ids.base_amount_currency",
        "tax_line_ids.tax_amount_currency",
    )
    def _compute_tax_amount_currency(self):
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
        "has_tax_distribution",
        "tax_line_ids.base_amount_currency",
        "tax_line_ids.tax_amount_currency",
    )
    def _compute_tax_amount(self):
        dist_expenses = self.filtered(
            lambda he: he.has_tax_distribution
            and any(dl.base_amount_currency for dl in he.tax_line_ids)
        )
        for expense in dist_expenses:
            tax_sum_currency = sum(expense.tax_line_ids.mapped("tax_amount_currency"))
            expense.tax_amount = expense.company_currency_id.round(
                tax_sum_currency * expense.currency_rate
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
                    _(
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
                    _(
                        "The sum of tax distribution line totals (%(distributed)s) "
                        "does not match the expense total amount (%(total)s) on "
                        'expense "%(name)s". '
                        "Please adjust the base amounts so that the totals match.",
                        distributed=expense.currency_id.format(distributed_total),
                        total=expense.currency_id.format(expense.total_amount_currency),
                        name=expense.name,
                    )
                )

    def action_submit_expenses(self):
        """Validate tax distribution totals before submission."""
        self._check_tax_distribution_total()
        return super().action_submit_expenses()

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
        move_vals, payment_vals = super()._prepare_payments_vals()
        if not self.has_tax_distribution:
            return move_vals, payment_vals

        AccountTax = self.env["account.tax"]
        rate = (
            abs(self.total_amount_currency / self.total_amount)
            if self.total_amount
            else 0.0
        )
        base_lines = [
            self._prepare_base_line_for_taxes_computation(
                price_unit=dist_line.total_amount_currency,
                quantity=1.0,
                account_id=self._get_base_account(),
                tax_ids=dist_line.tax_ids,
                rate=rate,
            )
            for dist_line in self.tax_line_ids
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id)
        AccountTax._add_accounting_data_in_base_lines_tax_details(
            base_lines,
            self.company_id,
            include_caba_tags=self.payment_mode == "company_account",
        )
        tax_results = AccountTax._prepare_tax_lines(base_lines, self.company_id)

        base_move_lines = [
            {
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
                "quantity": self.quantity,
            }
            for base_line, to_update in tax_results["base_lines_to_update"]
        ]
        tax_move_lines = tax_results["tax_lines_to_add"]
        # Rounding difference goes on the last base line, as the parent does
        # for its single base line.
        base_move_lines[-1]["balance"] = (
            self.total_amount
            - sum(line["balance"] for line in tax_move_lines)
            - sum(line["balance"] for line in base_move_lines[:-1])
        )
        outstanding_line = move_vals["line_ids"][-1]
        move_vals["line_ids"] = [
            Command.create(line) for line in base_move_lines + tax_move_lines
        ] + [outstanding_line]
        return move_vals, payment_vals


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _prepare_bills_vals(self):
        bills_vals = super()._prepare_bills_vals()
        if bills_vals["move_type"] != "in_invoice":
            return bills_vals
        dist_expenses = self.expense_line_ids.filtered("has_tax_distribution")
        line_ids = []
        for command in bills_vals["line_ids"]:
            expense = dist_expenses.browse(command[2].get("expense_id"))
            if expense in dist_expenses:
                line_ids.extend(
                    Command.create(line)
                    for line in expense._get_tax_distribution_move_lines_vals()
                )
            else:
                line_ids.append(command)
        bills_vals["line_ids"] = line_ids
        return bills_vals
