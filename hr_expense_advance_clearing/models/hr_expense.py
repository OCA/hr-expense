# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    advance = fields.Boolean()
    clearing_product_id = fields.Many2one(
        comodel_name="product.product",
        tracking=True,
        domain="[('can_be_expensed', '=', True),"
        "'|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        ondelete="restrict",
        help="Optional: On the clear advance, the clearing "
        "product will create default product line.",
    )
    # Clearing Field
    advance_id = fields.Many2one(
        comodel_name="hr.expense",
        string="Clear Advance",
        help="Show remaining advance of this employee",
    )
    advance_residual = fields.Monetary(
        string="Advance Remaining",
        currency_field="company_currency_id",
        related="advance_id.clearing_residual",
        help="Remaining amount of the selected advance.",
    )
    amount_to_pay = fields.Monetary(
        string="Amount to Pay",
        currency_field="company_currency_id",
        compute="_compute_amount_to_pay",
        help="Remaining amount to pay when the clearing exceeds the advance.",
    )

    # Advance Field
    clearing_residual = fields.Monetary(
        string="Amount to clear",
        currency_field="company_currency_id",
        compute="_compute_clearing_residual",
        store=True,
        help="Amount to clear of this advance in company currency",
    )
    clearing_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="advance_id",
        readonly=True,
        help="Show reference clearing on advance",
    )
    clearing_count = fields.Integer(
        compute="_compute_clearing_count",
    )
    return_count = fields.Integer(compute="_compute_return_count", compute_sudo=True)
    payment_return_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="advance_id",
        readonly=True,
        help="Show reference return advance on advance",
    )

    @api.depends("account_move_id.line_ids.amount_residual")
    def _compute_clearing_residual(self):
        for exp in self:
            emp_advance = exp._get_product_advance()
            residual_company = 0.0
            if emp_advance:
                property_account_expense_id = emp_advance.with_company(
                    exp.company_id
                ).property_account_expense_id
                for line in exp.sudo().account_move_id.line_ids:
                    if line.account_id == property_account_expense_id:
                        residual_company += line.amount_residual
            exp.clearing_residual = residual_company

    @api.depends("clearing_ids")
    def _compute_clearing_count(self):
        for exp in self:
            exp.clearing_count = len(exp.clearing_ids)

    @api.depends("payment_return_ids")
    def _compute_return_count(self):
        for sheet in self:
            sheet.return_count = len(sheet.payment_return_ids)

    @api.depends(
        "advance_id",
        "advance_id.clearing_residual",
        "total_amount",
        "account_move_id",
        "account_move_id.line_ids.account_id",
        "account_move_id.line_ids.amount_residual",
    )
    def _compute_amount_to_pay(self):
        for expense in self:
            expense.amount_to_pay = expense._get_advance_clearing_amount_to_pay()

    @api.depends(
        "amount_residual",
        "account_move_id.state",
        "account_move_id.payment_state",
        "account_move_id.line_ids.amount_residual",
        "account_move_id.line_ids.account_id.account_type",
        "approval_state",
        "advance_id",
    )
    def _compute_state(self):
        res = super()._compute_state()
        clearing_expenses = self.filtered(
            lambda expense: expense.advance_id
            and expense.account_move_id.state == "posted"
        )
        for expense in clearing_expenses:
            outstanding_lines = expense.account_move_id.line_ids.filtered(
                lambda line: line.account_id.account_type
                in ("asset_receivable", "liability_payable")
                and not line.company_currency_id.is_zero(line.amount_residual)
            )
            expense.state = "posted" if outstanding_lines else "paid"
        return res

    def _get_product_advance(self):
        return self.env.ref("hr_expense_advance_clearing.product_emp_advance", False)

    @api.constrains("advance", "advance_id")
    def _check_advance(self):
        for expense in self.filtered("advance"):
            if expense.advance_id:
                raise ValidationError(
                    self.env._(
                        "An expense cannot be both an advance and an advance clearing."
                    )
                )
            emp_advance = expense._get_product_advance()
            if not emp_advance.property_account_expense_id:
                raise ValidationError(
                    self.env._("Employee advance product has no payable account")
                )
            if expense.product_id != emp_advance:
                raise ValidationError(
                    self.env._("Employee advance, selected product is not valid")
                )
            if expense.account_id != emp_advance.property_account_expense_id:
                raise ValidationError(
                    self.env._(
                        "Employee advance, account must be the same payable account"
                    )
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

    @api.onchange("advance")
    def onchange_advance(self):
        self.tax_ids = False
        if self.advance:
            self.product_id = self._get_product_advance()

    @api.onchange("advance_id")
    def _onchange_advance_id(self):
        if not self.advance_id:
            return
        defaults = self.advance_id._prepare_advance_clearing_default_vals()
        for field, value in defaults.items():
            if value and not self[field]:
                self[field] = value

    def _prepare_advance_clearing_amounts(self):
        """Prepare the amounts used by the advance and payable lines."""
        self.ensure_one()

        advance_residual = self.advance_id.clearing_residual
        if self.company_currency_id.is_zero(advance_residual):
            raise ValidationError(
                self.env._(
                    "Advance %(advance)s has no remaining amount to clear.",
                    advance=self.advance_id.display_name,
                )
            )

        amount_to_clear = min(self.total_amount, advance_residual)
        amount_currency_to_clear = self.currency_id.round(
            self.total_amount_currency * amount_to_clear / self.total_amount
        )
        payable_balance = self.company_currency_id.round(
            self.total_amount - amount_to_clear
        )
        payable_amount_currency = self.currency_id.round(
            self.total_amount_currency - amount_currency_to_clear
        )
        return {
            "advance_residual": advance_residual,
            "amount_to_clear": amount_to_clear,
            "amount_currency_to_clear": amount_currency_to_clear,
            "payable_balance": payable_balance,
            "payable_amount_currency": payable_amount_currency,
        }

    def _prepare_advance_clearing_expense_line_vals(self, partner):
        """Prepare the expense base and tax lines."""
        self.ensure_one()
        account_tax = self.env["account.tax"]
        rate = (
            abs(self.total_amount_currency / self.total_amount)
            if self.total_amount
            else 0.0
        )
        base_line = self._prepare_base_line_for_taxes_computation(
            price_unit=self.total_amount_currency,
            quantity=1.0,
            account_id=self._get_base_account(),
            partner_id=partner,
            rate=rate,
        )
        base_lines = [base_line]
        account_tax._add_tax_details_in_base_lines(base_lines, self.company_id)
        account_tax._round_base_lines_tax_details(base_lines, self.company_id)
        account_tax._add_accounting_data_in_base_lines_tax_details(
            base_lines,
            self.company_id,
            include_caba_tags=False,
        )
        tax_results = account_tax._prepare_tax_lines(base_lines, self.company_id)

        move_line_vals = []
        base_move_line = {}
        for tax_base_line, to_update in tax_results["base_lines_to_update"]:
            base_move_line = {
                "name": self._get_move_line_name(),
                "account_id": tax_base_line["account_id"].id,
                "product_id": tax_base_line["product_id"].id,
                "analytic_distribution": tax_base_line["analytic_distribution"],
                "expense_id": self.id,
                "tax_ids": [Command.set(tax_base_line["tax_ids"].ids)],
                "tax_tag_ids": to_update["tax_tag_ids"],
                "amount_currency": to_update["amount_currency"],
                "balance": to_update["balance"],
                "currency_id": tax_base_line["currency_id"].id,
                "partner_id": partner.id,
            }
            move_line_vals.append(base_move_line)

        total_tax_line_balance = 0.0
        for tax_line in tax_results["tax_lines_to_add"]:
            total_tax_line_balance += tax_line["balance"]
            move_line_vals.append(tax_line)
        base_move_line["balance"] = self.total_amount - total_tax_line_balance
        return move_line_vals

    def _prepare_advance_clearing_advance_line_vals(
        self, accounting_date, partner, amounts
    ):
        """Prepare the line that clears the employee advance account."""
        self.ensure_one()
        account_advance = (
            self._get_product_advance()
            .with_company(self.company_id)
            .property_account_expense_id
        )
        return [
            {
                "name": self._get_move_line_name(),
                "account_id": account_advance.id,
                "balance": -amounts["amount_to_clear"],
                "amount_currency": -amounts["amount_currency_to_clear"],
                "currency_id": self.currency_id.id,
                "partner_id": partner.id,
                "date_maturity": accounting_date,
                "expense_id": self.id,
            }
        ]

    def _prepare_advance_clearing_payable_line_vals(
        self, accounting_date, partner, amounts
    ):
        """Prepare the payable line when clearing exceeds the advance."""
        self.ensure_one()
        if self.company_currency_id.is_zero(amounts["payable_balance"]):
            return []
        return [
            {
                "name": self._get_move_line_name(),
                "account_id": self._get_expense_account_destination(),
                "balance": -amounts["payable_balance"],
                "amount_currency": -amounts["payable_amount_currency"],
                "currency_id": self.currency_id.id,
                "partner_id": partner.id,
                "date_maturity": accounting_date,
                "expense_id": self.id,
            }
        ]

    def _prepare_advance_clearing_move_line_vals(self, accounting_date):
        """Prepare a balanced miscellaneous entry for an advance clearing."""
        self.ensure_one()
        amounts = self._prepare_advance_clearing_amounts()
        partner = self.employee_id.sudo().work_contact_id
        if not partner:
            raise ValidationError(
                self.env._(
                    "No work contact found for employee %(employee)s.",
                    employee=self.employee_id.display_name,
                )
            )

        return [
            *self._prepare_advance_clearing_expense_line_vals(partner),
            *self._prepare_advance_clearing_advance_line_vals(
                accounting_date, partner, amounts
            ),
            *self._prepare_advance_clearing_payable_line_vals(
                accounting_date, partner, amounts
            ),
        ]

    def _prepare_advance_clearing_move_vals(self, journal, accounting_date):
        self.ensure_one()
        if journal.type != "general":
            raise ValidationError(
                self.env._("The clearing journal must be a Miscellaneous journal.")
            )
        if journal.company_id != self.company_id:
            raise ValidationError(
                self.env._(
                    "The clearing journal and expense must belong to the same company."
                )
            )

        return {
            **self._prepare_move_vals(),
            "move_type": "entry",
            "journal_id": journal.id,
            "date": accounting_date,
            "ref": self.env._(
                "Advance Clearing: %(advance)s",
                advance=self.advance_id.display_name,
            ),
            "partner_id": self.employee_id.sudo().work_contact_id.id,
            "currency_id": self.currency_id.id,
            "company_id": self.company_id.id,
            "line_ids": [
                Command.create(vals)
                for vals in self._prepare_advance_clearing_move_line_vals(
                    accounting_date
                )
            ],
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

    def _create_advance_clearing_moves(self, journal, accounting_date):
        moves = (
            self.env["account.move"]
            .sudo()
            .create(
                [
                    expense._prepare_advance_clearing_move_vals(
                        journal, accounting_date
                    )
                    for expense in self
                ]
            )
        )
        for move in moves:
            move._message_set_main_attachment_id(
                move.attachment_ids,
                force=True,
                filter_xml=False,
            )
        return moves

    def _reconcile_advance_moves(self):
        for expense in self:
            account_advance = (
                expense._get_product_advance()
                .with_company(expense.company_id)
                .property_account_expense_id
            )
            partner = expense.employee_id.sudo().work_contact_id
            move_lines = (
                expense.advance_id.account_move_id.line_ids
                | expense.account_move_id.line_ids
            ).filtered(
                lambda line, account=account_advance, contact=partner: (
                    line.account_id == account
                    and line.partner_id == contact
                    and not line.reconciled
                )
            )
            if move_lines.filtered("debit") and move_lines.filtered("credit"):
                move_lines.sudo().reconcile()

    def _post_wizard(self):
        clearing_expenses = self.filtered("advance_id")
        if not clearing_expenses:
            return super()._post_wizard()
        if clearing_expenses != self:
            raise ValidationError(
                self.env._(
                    "Advance clearing and normal expenses must be posted separately."
                )
            )

        clearing_expenses = clearing_expenses.with_context(
            advance_clearing=True,
            active_model="hr.expense",
            active_id=clearing_expenses[:1].id,
            active_ids=clearing_expenses.ids,
        )
        return super(HrExpense, clearing_expenses)._post_wizard()

    def _check_can_approve(self):
        res = super()._check_can_approve()
        for expense in self.filtered("advance_id"):
            if (
                expense.company_currency_id.compare_amounts(
                    expense.advance_id.clearing_residual, 0.0
                )
                <= 0
            ):
                raise ValidationError(
                    self.env._(
                        "Advance %(advance)s has no remaining amount to clear.",
                        advance=expense.advance_id.display_name,
                    )
                )
        return res

    def _get_advance_clearing_payable_lines(self):
        """Return outstanding payable lines created by an advance clearing."""
        self.ensure_one()
        if not self.advance_id or not self.account_move_id:
            return self.env["account.move.line"]

        payable_account_id = self._get_expense_account_destination()
        return self.account_move_id.line_ids.filtered(
            lambda line: line.account_id.id == payable_account_id
            and line.amount_residual < 0.0
            and not line.company_currency_id.is_zero(line.amount_residual)
        )

    def _get_advance_clearing_amount_to_pay(self):
        """Return estimated or posted outstanding amount for a clearing."""
        self.ensure_one()
        if not self.advance_id:
            return 0.0
        if self.account_move_id:
            payable_lines = self._get_advance_clearing_payable_lines()
            return -sum(payable_lines.mapped("amount_residual"))
        return max(self.total_amount - self.advance_id.clearing_residual, 0.0)

    def action_pay(self):
        self.ensure_one()
        if not self.advance_id:
            return super().action_pay()

        payable_lines = self._get_advance_clearing_payable_lines()
        if not payable_lines:
            raise ValidationError(
                self.env._("There is no remaining amount to pay for this clearing.")
            )

        return payable_lines.action_register_payment(
            ctx={
                "default_partner_bank_id": self.account_move_id.partner_bank_id.id,
            }
        )

    def action_return_advance(self):
        self.ensure_one()
        if not self.advance or self.state != "paid":
            raise ValidationError(
                self.env._("Only a paid employee advance can be returned.")
            )

        account_advance = (
            self._get_product_advance()
            .with_company(self.company_id)
            .property_account_expense_id
        )
        if not account_advance:
            raise ValidationError(
                self.env._("Employee advance product has no advance account.")
            )
        if not account_advance.reconcile:
            raise ValidationError(
                self.env._(
                    "Allow Reconciliation must be enabled "
                    "on the employee advance account."
                )
            )

        advance_lines = self.account_move_id.line_ids.filtered(
            lambda line: line.account_id == account_advance
            and line.amount_residual > 0.0
            and not line.company_currency_id.is_zero(line.amount_residual)
        )
        if not advance_lines:
            raise ValidationError(
                self.env._("There is no remaining advance amount to return.")
            )

        action = advance_lines.action_register_payment(
            ctx={
                "hr_return_advance": True,
                "hr_return_advance_id": self.id,
                "hr_return_advance_account_id": account_advance.id,
            }
        )
        action["name"] = self.env._("Return Advance")
        return action

    def _prepare_advance_clearing_default_vals(self):
        self.ensure_one()
        if not self.clearing_product_id:
            return {}
        return {
            "product_id": self.clearing_product_id.id,
            "name": self.clearing_product_id.display_name,
        }

    def _get_context_clear_advance(self):
        defaults = self._prepare_advance_clearing_default_vals()
        context = dict(
            self.env.context,
            default_advance=False,
            default_advance_id=self.id,
            default_employee_id=self.employee_id.id,
            default_company_id=self.company_id.id,
            default_payment_mode="own_account",
        )
        context.update({f"default_{field}": value for field, value in defaults.items()})
        return context

    def open_clear_advance(self):
        self.ensure_one()

        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Advance Clearing"),
            "res_model": "hr.expense",
            "view_mode": "form",
            "views": [
                (
                    self.env.ref("hr_expense.hr_expense_view_form").id,
                    "form",
                )
            ],
            "target": "current",
            "context": self._get_context_clear_advance(),
        }

    def action_open_clearings(self):
        self.ensure_one()
        return {
            "name": self.env._("Clearing"),
            "type": "ir.actions.act_window",
            "res_model": "hr.expense",
            "view_mode": "list,form",
            "domain": [("id", "in", self.clearing_ids.ids)],
        }

    def action_open_payment_return(self):
        self.ensure_one()
        return {
            "name": self.env._("Payment Return"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.payment_return_ids.ids)],
        }
