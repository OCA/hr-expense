# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from collections import defaultdict

from odoo import Command, api, fields, models
from odoo.exceptions import UserError, ValidationError


class HrExpense(models.Model):
    """Add advance/clearing handling: an advance expense paid to the employee
    is cleared by reconciling later regular expenses against it."""

    _inherit = "hr.expense"

    expense_type = fields.Selection(
        selection=[("expense", "Expense"), ("advance", "Advance")],
        default="expense",
        required=True,
        tracking=True,
        help="An 'advance' is money paid to the employee up front. Regular "
        "'expense' records are either reimbursements or clearings against "
        "a prior advance (when clearing_advance_id is set).",
    )
    clearing_advance_id = fields.Many2one(
        comodel_name="hr.expense",
        domain="[('expense_type', '=', 'advance'),"
        " ('employee_id', '=', employee_id),"
        " ('clearing_residual', '>', 0.0)]",
        tracking=True,
        ondelete="restrict",
        help="When set on a regular expense, this expense clears against "
        "the referenced advance. Only advances of the same employee "
        "with residual > 0 are selectable.",
    )
    clearing_expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="clearing_advance_id",
        string="Clearing Expenses",
        readonly=True,
        help="Expenses cleared against this advance.",
    )
    clearing_count = fields.Integer(compute="_compute_clearing_count")
    payment_return_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="advance_id",
        string="Returned Payments",
        readonly=True,
        help="Refund payments returning unused advance money to the company.",
    )
    return_count = fields.Integer(compute="_compute_return_count", compute_sudo=True)

    cleared_amount = fields.Monetary(
        compute="_compute_clearing_residual",
        store=True,
        help="Sum of clearing expenses' totals (company currency).",
    )
    returned_amount = fields.Monetary(
        compute="_compute_clearing_residual",
        store=True,
        help="Sum of return-advance payments (company currency).",
    )
    clearing_residual = fields.Monetary(
        string="Amount to Clear",
        compute="_compute_clearing_residual",
        store=True,
        help="Advance amount remaining to be cleared or returned.",
    )
    advance_residual = fields.Monetary(
        string="Advance Remaining",
        related="clearing_advance_id.clearing_residual",
        store=True,
        help="Remaining amount on the linked advance (for clearing expenses).",
    )
    amount_payable = fields.Monetary(
        string="Payable Amount",
        compute="_compute_amount_payable",
        help="Register-payment amount after subtracting the cleared advance.",
    )
    clearing_product_id = fields.Many2one(
        comodel_name="product.product",
        tracking=True,
        domain="[('can_be_expensed', '=', True),"
        " '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete="restrict",
        help="Optional: when set on an advance, this product is used as the "
        "default for clearing expense lines.",
    )

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _get_product_advance(self):
        return self.env.ref("hr_expense_advance_clearing.product_emp_advance", False)

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("expense_type", "product_id", "tax_ids", "payment_mode")
    def _check_advance(self):
        """An advance expense must use the Employee Advance product, no
        taxes, and be employee-paid."""
        emp_advance = self._get_product_advance()
        if not emp_advance:
            return True
        for expense in self.filtered(lambda e: e.expense_type == "advance"):
            if not emp_advance.property_account_expense_id:
                raise ValidationError(
                    self.env._("Employee advance product has no payable account")
                )
            if expense.product_id != emp_advance:
                raise ValidationError(
                    self.env._("Employee advance, selected product is not valid")
                )
            if expense.tax_ids:
                raise ValidationError(
                    self.env._("Employee advance, all taxes must be removed")
                )
            if expense.payment_mode != "own_account":
                raise ValidationError(
                    self.env._("Employee advance, paid by must be employee")
                )
        return True

    @api.constrains("clearing_advance_id", "expense_type", "employee_id")
    def _check_clearing(self):
        """A clearing expense must be 'expense' type, must reference an
        advance of the same employee, and the advance must be paid."""
        for expense in self.filtered("clearing_advance_id"):
            if expense.expense_type == "advance":
                raise ValidationError(
                    self.env._("An advance cannot itself clear another advance.")
                )
            advance = expense.clearing_advance_id
            if advance.employee_id != expense.employee_id:
                raise ValidationError(
                    self.env._("The linked advance must belong to the same employee.")
                )

    # -------------------------------------------------------------------------
    # Onchanges + defaults
    # -------------------------------------------------------------------------

    @api.onchange("expense_type")
    def _onchange_expense_type(self):
        if self.expense_type == "advance":
            emp_advance = self._get_product_advance()
            if emp_advance:
                self.product_id = emp_advance
            self.tax_ids = False
            self.payment_mode = "own_account"
            self.clearing_advance_id = False

    @api.onchange("clearing_advance_id")
    def _onchange_clearing_advance_id(self):
        """Pre-fill clearing product from the advance if it has one set."""
        advance = self.clearing_advance_id
        if advance and advance.clearing_product_id and not self.product_id:
            self.product_id = advance.clearing_product_id

    # -------------------------------------------------------------------------
    # Computes
    # -------------------------------------------------------------------------

    @api.depends(
        "expense_type",
        "total_amount_currency",
        "clearing_expense_ids.total_amount_currency",
        "clearing_expense_ids.state",
        "payment_return_ids.amount",
        "payment_return_ids.state",
    )
    def _compute_clearing_residual(self):
        for expense in self:
            if expense.expense_type != "advance":
                expense.cleared_amount = 0.0
                expense.returned_amount = 0.0
                expense.clearing_residual = 0.0
                continue
            cleared = sum(
                expense.clearing_expense_ids.filtered(
                    lambda e: e.state not in ("draft", "submitted", "refused")
                ).mapped("total_amount_currency")
            )
            returned = sum(
                expense.payment_return_ids.filtered(
                    lambda p: p.state in ("in_process", "paid")
                ).mapped("amount")
            )
            expense.cleared_amount = cleared
            expense.returned_amount = returned
            # Clamp at 0: over-clearing consumes the whole advance (the excess
            # is the employee's out-of-pocket, booked to the payable), so the
            # advance has nothing left rather than a negative residual.
            expense.clearing_residual = max(
                expense.total_amount_currency - cleared - returned, 0.0
            )

    @api.depends("clearing_expense_ids")
    def _compute_clearing_count(self):
        for expense in self:
            expense.clearing_count = len(expense.clearing_expense_ids)

    @api.depends("payment_return_ids")
    def _compute_return_count(self):
        for expense in self:
            expense.return_count = len(expense.payment_return_ids)

    @api.depends(
        "total_amount_currency",
        "clearing_advance_id.clearing_residual",
    )
    def _compute_amount_payable(self):
        """For a clearing expense: payable = total − advance available."""
        for expense in self:
            if not expense.clearing_advance_id:
                expense.amount_payable = 0.0
                continue
            residual = expense.clearing_advance_id.clearing_residual
            expense.amount_payable = max(expense.total_amount_currency - residual, 0.0)

    # -------------------------------------------------------------------------
    # Server actions
    # -------------------------------------------------------------------------

    def action_return_advance(self):
        """Open Register Payment for the remaining advance residual so the
        employee can refund what they didn't spend."""
        self.ensure_one()
        if self.expense_type != "advance":
            raise UserError(self.env._("Only advance expenses can be returned."))
        if self.clearing_residual <= 0:
            raise UserError(self.env._("This advance has no residual to return."))
        # The register-payment wizard must be invoked on account.move(.line)
        # records: target the advance's still-open employee-advance line so the
        # returned payment reconciles against it.
        account_advance = self._get_product_advance().property_account_expense_id
        advance_line = self.account_move_id.line_ids.filtered(
            lambda line: line.account_id == account_advance and not line.reconciled
        )
        if not advance_line:
            raise UserError(self.env._("No open advance line found to return."))
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Return Advance"),
            "res_model": "account.payment.register",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "account.move.line",
                "active_ids": advance_line.ids,
                "default_partner_type": "customer",
                "default_partner_id": self.employee_id.sudo().work_contact_id.id,
                "default_amount": self.clearing_residual,
                "default_currency_id": self.currency_id.id,
                "default_advance_id": self.id,
                "hr_return_advance": 1,
            },
        }

    def action_view_clearings(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Clearing Expenses"),
            "res_model": "hr.expense",
            "view_mode": "list,form",
            "domain": [("id", "in", self.clearing_expense_ids.ids)],
        }

    def action_view_returns(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Returned Payments"),
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.payment_return_ids.ids)],
        }

    # -------------------------------------------------------------------------
    # Posting: clearing expenses book as journal entries against the advance
    # -------------------------------------------------------------------------

    def _prepare_receipts_vals(self):
        """Clearing expenses post as ``entry`` moves that credit the
        employee-advance account, not as vendor receipts: the clearing
        consumes the advance directly instead of raising a fresh payable.
        Regular expenses keep core's ``in_receipt`` behaviour."""
        clearing = self.filtered("clearing_advance_id")
        regular = self - clearing
        vals_list = (
            super(HrExpense, regular)._prepare_receipts_vals() if regular else []
        )
        by_advance = defaultdict(self.browse)
        for expense in clearing:
            by_advance[expense.clearing_advance_id] |= expense
        for advance, expenses in by_advance.items():
            vals_list.append(expenses._prepare_clearing_entry_vals(advance))
        return vals_list

    def _get_advance_analytic_distribution(self, advance_move):
        """Return the advance move's analytic distribution when all of its
        lines share a single one, so the clearing credit to the advance
        account carries the same analytic as the original advance."""
        analytics = [
            a for a in advance_move.line_ids.mapped("analytic_distribution") if a
        ]
        if len({str(a) for a in analytics}) == 1:
            return analytics[0]
        return False

    def _prepare_clearing_entry_vals(self, advance):
        """Build one ``entry`` move debiting each clearing expense's account
        and crediting the employee-advance account (capped at the advance
        residual; any excess goes to the employee payable so it can still be
        reimbursed). Taxes are reflected via base tags only."""
        emp_advance = self._get_product_advance()
        account_advance = emp_advance.property_account_expense_id
        partner = advance.employee_id.sudo().work_contact_id
        payable_account = partner.property_account_payable_id
        # Amounts are booked in the company currency; a clearing expense in a
        # foreign currency is converted (total_amount) and not tracked in its
        # own currency on the entry. Multi-currency clearing is out of scope.
        company_currency = self.company_id.currency_id
        # The advance must be posted first: the entry credits the advance
        # account and is reconciled against the advance's debit, so without a
        # posted advance the credit would dangle.
        advance_move = advance.account_move_id
        if advance_move.state != "posted":
            raise UserError(
                self.env._(
                    "Post the advance %(name)s before clearing expenses against it.",
                    name=advance.name,
                )
            )
        advance_analytic = self._get_advance_analytic_distribution(advance_move)
        # Cap against the advance's still-unreconciled balance on the advance
        # account (its real GL residual), not the count-based clearing_residual
        # field — that field already nets out the approved clearings being
        # posted now, which would double-count and under-credit the advance.
        advance_lines = advance_move.line_ids.filtered(
            lambda line: line.account_id == account_advance
        )
        advance_to_clear = sum(advance_lines.mapped("amount_residual"))
        line_cmds = []
        for expense in self:
            name = expense._get_move_line_name()
            taxes = expense.tax_ids.with_context(round=True).compute_all(
                expense.price_unit or expense.total_amount,
                expense.currency_id,
                expense.quantity if expense.price_unit else 1,
                expense.product_id,
            )
            line_cmds.append(
                Command.create(
                    {
                        "name": name,
                        "account_id": expense._get_base_account().id,
                        "debit": expense.total_amount,
                        "credit": 0.0,
                        "currency_id": company_currency.id,
                        "product_id": expense.product_id.id,
                        "product_uom_id": expense.product_uom_id.id,
                        "analytic_distribution": expense.analytic_distribution,
                        "tax_ids": [Command.set(expense.tax_ids.ids)],
                        "tax_tag_ids": [Command.set(taxes["base_tags"])],
                        "expense_id": expense.id,
                        "partner_id": partner.id,
                    }
                )
            )
            credit = expense.total_amount
            cleared = max(min(credit, advance_to_clear), 0.0)
            advance_to_clear -= cleared
            if cleared:
                line_cmds.append(
                    Command.create(
                        {
                            "name": name,
                            "account_id": account_advance.id,
                            "debit": 0.0,
                            "credit": cleared,
                            "currency_id": company_currency.id,
                            "analytic_distribution": advance_analytic,
                            "expense_id": expense.id,
                            "partner_id": partner.id,
                        }
                    )
                )
            remainder = credit - cleared
            if remainder:
                line_cmds.append(
                    Command.create(
                        {
                            "name": name,
                            "account_id": payable_account.id,
                            "debit": 0.0,
                            "credit": remainder,
                            "currency_id": company_currency.id,
                            "expense_id": expense.id,
                            "partner_id": partner.id,
                        }
                    )
                )
        return {
            **self._prepare_move_vals(),
            "ref": self.env._("Advance clearing: %(name)s", name=advance.name),
            "move_type": "entry",
            "partner_id": partner.id,
            "currency_id": company_currency.id,
            "company_id": self.company_id.id,
            "line_ids": line_cmds,
        }
