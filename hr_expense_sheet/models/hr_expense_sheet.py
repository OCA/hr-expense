# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import format_date
from odoo.tools.misc import clean_context

from odoo.addons.hr_expense.models.hr_expense import EXPENSE_APPROVAL_STATE


class HrExpenseSheet(models.Model):
    _name = "hr.expense.sheet"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]
    _description = "Expense Report"
    _order = "accounting_date desc, id desc"
    _check_company_auto = True

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id

    @api.model
    def _default_journal_id(self):
        """
        The journal is determining the company of the accounting entries generated
        from expense.
        We need to force journal company and expense sheet company to be the same.
        """
        company_journal_id = self.env.company.expense_journal_id
        if company_journal_id:
            return company_journal_id.id
        default_company_id = self.default_get(["company_id"])["company_id"]
        journal = (
            self.env["account.journal"]
            .sudo()
            .search(
                [
                    *self.env["account.journal"]
                    .sudo()
                    ._check_company_domain(default_company_id),
                    ("type", "=", "purchase"),
                ],
                limit=1,
            )
        )
        return journal.id

    name = fields.Char(string="Expense Report Summary", required=True, tracking=True)
    expense_line_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="sheet_id",
        string="Expense Lines",
        copy=False,
    )
    nb_expense = fields.Integer(
        compute="_compute_nb_expense", string="Number of Expenses"
    )
    state = fields.Selection(
        selection=[
            ("draft", "To Submit"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("posted", "Posted"),
            ("in_payment", "In Payment"),
            ("paid", "Paid"),
            ("refused", "Refused"),
        ],
        string="Status",
        compute="_compute_state",
        store=True,
        readonly=True,
        index=True,
        required=True,
        default="draft",
        tracking=True,
        copy=False,
    )
    approval_state = fields.Selection(
        selection=EXPENSE_APPROVAL_STATE, copy=False, readonly=True
    )
    approval_date = fields.Datetime(readonly=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        required=True,
        readonly=True,
        default=lambda self: self.env.company,
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        required=True,
        readonly=True,
        default=lambda self: self._default_employee_id(),
        domain=[("filter_for_expense", "=", True)],
        check_company=True,
        tracking=True,
    )
    department_id = fields.Many2one(
        comodel_name="hr.department",
        related="employee_id.department_id",
        string="Department",
        store=True,
        copy=False,
    )
    manager_id = fields.Many2one(
        comodel_name="res.users",
        compute="_compute_manager_id",
        store=True,
        domain=lambda self: [
            ("share", "=", False),
            "|",
            ("employee_id.expense_manager_id", "in", self.env.user.id),
            (
                "all_group_ids",
                "in",
                self.env.ref("hr_expense.group_hr_expense_team_approver").ids,
            ),
        ],
        copy=False,
        tracking=True,
    )
    product_ids = fields.Many2many(
        comodel_name="product.product",
        string="Categories",
        compute="_compute_product_ids",
        search="_search_product_ids",
        check_company=True,
    )
    # === Amount fields === #
    tax_amount_currency = fields.Monetary(
        string="Tax amount in Currency",
        currency_field="currency_id",
        compute="_compute_tax_amount_currency",
        precompute=True,
        store=True,
        help="Tax amount in currency",
    )
    tax_amount = fields.Monetary(
        string="Tax amount",
        currency_field="company_currency_id",
        compute="_compute_tax_amount",
        precompute=True,
        store=True,
        help="Tax amount in company currency",
    )
    total_amount_currency = fields.Monetary(
        string="Total In Currency",
        currency_field="currency_id",
        compute="_compute_total_amount_currency",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
    )
    total_amount = fields.Monetary(
        string="Total",
        currency_field="company_currency_id",
        compute="_compute_total_amount",
        precompute=True,
        store=True,
        readonly=False,
        tracking=True,
    )
    untaxed_amount_currency = fields.Monetary(
        string="Total Untaxed Amount In Currency",
        currency_field="currency_id",
        compute="_compute_untaxed_amount_currency",
        precompute=True,
        store=True,
    )
    untaxed_amount = fields.Monetary(
        string="Total Untaxed Amount",
        currency_field="currency_id",
        compute="_compute_untaxed_amount",
        precompute=True,
        store=True,
    )
    amount_residual = fields.Monetary(
        string="Amount Due",
        currency_field="company_currency_id",
        compute="_compute_amount_residual",
        store=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        store=True,
        readonly=True,
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Report Company Currency",
    )
    is_multiple_currency = fields.Boolean(
        string="Handle lines with different currencies",
        compute="_compute_is_multiple_currency",
    )
    # === Account fields === #
    payment_mode = fields.Selection(
        related="expense_line_ids.payment_mode",
        string="Paid By",
        tracking=True,
        readonly=True,
    )
    employee_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        default=lambda self: self._default_journal_id(),
        check_company=True,
        domain=[("type", "=", "purchase")],
        help="The journal used when the expense is paid by employee.",
    )
    selectable_payment_method_line_ids = fields.Many2many(
        comodel_name="account.payment.method.line",
        compute="_compute_selectable_payment_method_line_ids",
    )
    payment_method_line_id = fields.Many2one(
        comodel_name="account.payment.method.line",
        string="Payment Method",
        compute="_compute_payment_method_line_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', selectable_payment_method_line_ids)]",
        help="The payment method used when the expense is paid by the company.",
    )
    attachment_ids = fields.One2many(
        comodel_name="ir.attachment",
        inverse_name="res_id",
        domain="[('res_model', '=', 'hr.expense.sheet')]",
        string="Attachments of expenses",
    )
    accounting_date = fields.Date(
        string="Expense Report Date",
        help="Specify the bill date of the related vendor bill.",
    )
    account_move_ids = fields.One2many(
        string="Journal Entries",
        comodel_name="account.move",
        inverse_name="expense_sheet_id",
        readonly=True,
    )
    nb_account_move = fields.Integer(
        string="Number of Journal Entries", compute="_compute_nb_account_move"
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Expense Journal",
        compute="_compute_journal_id",
        store=True,
        check_company=True,
    )
    # === Security fields === #
    can_reset = fields.Boolean(compute="_compute_can_reset")
    can_approve = fields.Boolean(compute="_compute_can_approve")
    cannot_approve_reason = fields.Char(compute="_compute_cannot_approve_reason")
    is_editable = fields.Boolean(
        string="Expense Lines Are Editable By Current User",
        compute="_compute_is_editable",
    )

    @api.depends("expense_line_ids.tax_amount_currency")
    def _compute_tax_amount_currency(self):
        for sheet in self:
            sheet.tax_amount_currency = sum(
                sheet.expense_line_ids.mapped("tax_amount_currency")
            )

    @api.depends("expense_line_ids.tax_amount")
    def _compute_tax_amount(self):
        for sheet in self:
            sheet.tax_amount = sum(sheet.expense_line_ids.mapped("tax_amount"))

    @api.depends("expense_line_ids.total_amount_currency")
    def _compute_total_amount_currency(self):
        for sheet in self:
            sheet.total_amount_currency = sum(
                sheet.expense_line_ids.mapped("total_amount_currency")
            )

    @api.depends("expense_line_ids.total_amount")
    def _compute_total_amount(self):
        for sheet in self:
            sheet.total_amount = sum(sheet.expense_line_ids.mapped("total_amount"))

    @api.depends("expense_line_ids.untaxed_amount_currency")
    def _compute_untaxed_amount_currency(self):
        for sheet in self:
            sheet.untaxed_amount_currency = sum(
                sheet.expense_line_ids.mapped("untaxed_amount_currency")
            )

    @api.depends("expense_line_ids.untaxed_amount")
    def _compute_untaxed_amount(self):
        for sheet in self:
            sheet.untaxed_amount = sum(sheet.expense_line_ids.mapped("untaxed_amount"))

    @api.depends("expense_line_ids.amount_residual")
    def _compute_amount_residual(self):
        for sheet in self:
            sheet.amount_residual = sum(
                sheet.expense_line_ids.mapped("amount_residual")
            )

    @api.depends("selectable_payment_method_line_ids")
    def _compute_payment_method_line_id(self):
        for sheet in self:
            sheet.payment_method_line_id = sheet.selectable_payment_method_line_ids[:1]

    @api.depends("employee_journal_id", "payment_method_line_id")
    def _compute_journal_id(self):
        for sheet in self:
            if sheet.payment_mode == "company_account":
                sheet.journal_id = sheet.payment_method_line_id.journal_id
            else:
                sheet.journal_id = sheet.employee_journal_id

    @api.depends("expense_line_ids")
    def _compute_selectable_payment_method_line_ids(self):
        for sheet in self:
            sheet.selectable_payment_method_line_ids = (
                sheet.expense_line_ids.selectable_payment_method_line_ids
            )

    @api.depends("expense_line_ids.state")
    def _compute_state(self):
        for sheet in self:
            expenses = sheet.expense_line_ids
            if not expenses:
                sheet.state = "draft"
            elif all(expense.state == "draft" for expense in expenses):
                sheet.state = "draft"
            elif all(expense.state == "submitted" for expense in expenses):
                sheet.state = "submitted"
            elif all(expense.state == "approved" for expense in expenses):
                sheet.state = "approved"
            elif all(expense.state == "posted" for expense in expenses):
                sheet.state = "posted"
            elif any(expense.state == "in_payment" for expense in expenses):
                sheet.state = "in_payment"
            elif all(expense.state == "paid" for expense in expenses):
                sheet.state = "paid"
            elif all(expense.state == "refused" for expense in expenses):
                sheet.state = "refused"

    @api.depends("employee_id")
    def _compute_manager_id(self):
        for sheet in self.filtered("expense_line_ids"):
            expense = sheet.expense_line_ids[0]
            sheet.manager_id = expense._get_default_responsible_for_approval()

    @api.depends("expense_line_ids.currency_id", "company_currency_id")
    def _compute_currency_id(self):
        for sheet in self:
            if (
                not sheet.expense_line_ids
                or sheet.is_multiple_currency
                or sheet.payment_mode == "own_account"
            ):
                sheet.currency_id = sheet.company_currency_id
            else:
                sheet.currency_id = sheet.expense_line_ids[:1].currency_id

    @api.depends("expense_line_ids.currency_id")
    def _compute_is_multiple_currency(self):
        for sheet in self:
            sheet.is_multiple_currency = (
                any(sheet.expense_line_ids.mapped("is_multiple_currency"))
                or len(sheet.expense_line_ids.mapped("currency_id")) > 1
            )

    @api.depends("employee_id")
    def _compute_can_reset(self):
        is_expense_user = self.env.user.has_group(
            "hr_expense.group_hr_expense_team_approver"
        )
        for sheet in self:
            sheet.can_reset = (
                is_expense_user
                if is_expense_user
                else sheet.employee_id.expense_manager_id == self.env.user
            )

    @api.depends_context("uid")
    @api.depends("cannot_approve_reason")
    def _compute_can_approve(self):
        for sheet in self:
            sheet.can_approve = not sheet.cannot_approve_reason

    @api.depends_context("uid")
    @api.depends("employee_id")
    def _compute_cannot_approve_reason(self):
        for sheet in self:
            if sheet.expense_line_ids:
                expense = sheet.expense_line_ids[0]
                cannot_reason_per_record_id = expense._get_cannot_approve_reason()
                sheet.cannot_approve_reason = cannot_reason_per_record_id[expense.id]
            else:
                sheet.cannot_approve_reason = False

    @api.depends("expense_line_ids")
    def _compute_nb_expense(self):
        expense_data = self.env["hr.expense"]._read_group(
            [("sheet_id", "in", self.ids)],
            ["sheet_id"],
            ["__count"],
        )
        result = {sheet.id: count for sheet, count in expense_data}
        for sheet in self:
            sheet.nb_expense = result.get(sheet.id, 0)

    @api.depends("account_move_ids")
    def _compute_nb_account_move(self):
        move_data = self.env["account.move"]._read_group(
            [("expense_sheet_id", "in", self.ids)],
            ["expense_sheet_id"],
            ["__count"],
        )
        result = {sheet.id: count for sheet, count in move_data}
        for sheet in self:
            sheet.nb_account_move = result.get(sheet.id, 0)

    @api.depends_context("uid")
    @api.depends("employee_id", "manager_id", "state")
    def _compute_is_editable(self):
        is_hr_admin = self.env.user.has_group(
            "hr_expense.group_hr_expense_manager"
        ) or self.env.user.has_group("base.group_system")
        is_approver = self.env.user.has_group("hr_expense.group_hr_expense_user")
        for sheet in self:
            if sheet.state not in {"draft", "submitted", "approved"}:
                # Not editable
                sheet.is_editable = False
                continue
            if is_hr_admin or self.env.su:
                # Administrator-level users are not restricted
                sheet.is_editable = True
                continue
            employee = sheet.employee_id
            is_own_sheet = employee.user_id == self.env.user
            if is_own_sheet and sheet.state == "draft":
                # Anyone can edit their own draft sheet
                sheet.is_editable = True
                continue
            managers = (
                sheet.manager_id
                | employee.expense_manager_id
                | employee.sudo().department_id.manager_id.user_id.sudo(self.env.su)
            )
            if is_approver:
                managers |= self.env.user
            if not is_own_sheet and self.env.user in managers:
                # If Approver-level or designated manager, can edit other people sheet
                sheet.is_editable = True
                continue
            sheet.is_editable = False

    @api.depends("expense_line_ids")
    def _compute_product_ids(self):
        for sheet in self:
            sheet.product_ids = sheet.expense_line_ids.mapped("product_id")

    @api.constrains("expense_line_ids")
    def _check_payment_mode(self):
        for sheet in self.filtered(lambda x: x.expense_line_ids):
            expenses = sheet.mapped("expense_line_ids")
            if any(
                expense.payment_mode != expense[:1].payment_mode for expense in expenses
            ):
                raise ValidationError(
                    self.env._(
                        "All expenses in an expense report must have the same "
                        "'paid by' criteria."
                    )
                )

    @api.constrains("expense_line_ids", "employee_id")
    def _check_employee(self):
        for sheet in self.filtered(lambda x: x.expense_line_ids):
            if sheet.expense_line_ids.employee_id - sheet.employee_id:
                raise ValidationError(
                    self.env._("You cannot add expenses of another employee.")
                )

    @api.constrains("expense_line_ids", "company_id")
    def _check_expense_lines_company(self):
        for sheet in self.filtered(lambda x: x.expense_line_ids):
            if sheet.expense_line_ids.company_id - sheet.company_id:
                raise ValidationError(
                    self.env._(
                        "An expense report must contain only lines from the same "
                        "company."
                    )
                )

    @api.onchange("expense_line_ids")
    def _update_sheet_name(self):
        """Set the sheet name to the computed default sheet name when no name is
        specified.
        """
        expense_lines = self.expense_line_ids
        if not self.name and expense_lines:
            self.name = self._get_default_sheet_name(expense_lines)

    @api.model
    def _get_default_sheet_name(self, expenses_to_report):
        """Computes the default name for a new expense sheet from the expenses name
        or dates
        """
        if len(expenses_to_report) == 1:
            sheet_name = expenses_to_report.name
        else:
            dates = expenses_to_report.mapped("date")
            if (
                False in dates
            ):  # If at least one date isn't set, we don't set a default name
                return False
            min_date = format_date(self.env, min(dates))
            max_date = format_date(self.env, max(dates))
            if min_date == max_date:
                sheet_name = min_date
            else:
                sheet_name = self.env._(
                    "%(date_from)s - %(date_to)s", date_from=min_date, date_to=max_date
                )
        return sheet_name

    @api.model
    def _search_product_ids(self, operator, value):
        if operator == "in" and not isinstance(value, list):
            value = [value]
        return [("expense_line_ids.product_id", operator, value)]

    # ----------------------------------------
    # ORM Overrides
    # ----------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        context = clean_context(self.env.context)
        context.update(
            {
                "mail_create_nosubscribe": True,
                "mail_auto_subscribe_no_notify": True,
            }
        )
        sheets = super(HrExpenseSheet, self.with_context(**context)).create(vals_list)
        sheets.activity_update()
        return sheets

    def write(self, values):
        res = super().write(values)
        user_is_accountant = self.env.user.has_group("account.group_account_user")
        edit_lines = "expense_line_ids" in values
        edit_states = "state" in values or "approval_state" in values
        # Forbids (un)linking expenses from an approved sheet if you're not an
        # accountant
        if (
            edit_lines
            and not user_is_accountant
            and set(self.mapped("state")) - {"draft", "submitted"}
        ):
            raise AccessError(
                self.env._(
                    "You do not have the rights to add or remove any expenses on an "
                    "approved or paid expense report."
                )
            )
        # Ensures there is no empty expense report in a state different from draft or
        # refused
        if edit_states or edit_lines:
            for sheet in self.filtered(lambda sheet: not sheet.expense_line_ids):
                if sheet.state in {
                    "submitted",
                    "approved",
                    "posted",
                    "in_payment",
                    "paid",
                }:
                    # Empty expense report in a state different from draft or can
                    # refused
                    if (
                        edit_lines and not sheet.expense_line_ids
                    ):  # If you try to remove all expenses from the sheet
                        raise UserError(
                            self.env._(
                                "You cannot remove all expenses from a submitted, "
                                "approved or paid expense report."
                            )
                        )
                    else:
                        # If you try to submit, approved, posted or pay an empty sheet
                        raise UserError(
                            self.env._(
                                "This expense report is empty. You cannot submit or "
                                "approve an empty expense report."
                            )
                        )
        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_or_paid(self):
        for expense in self:
            if expense.state in {"posted", "in_payment", "paid"}:
                raise UserError(
                    self.env._("You cannot delete a posted or paid expense.")
                )

    # --------------------------------------------
    # Mail Thread
    # --------------------------------------------

    def _track_subtype(self, init_values):
        # Similar to what happens in hr.expense but with sheet
        self.ensure_one()
        if "state" not in init_values:
            return super()._track_subtype(init_values)
        match self.state:
            case "draft":
                return self.env.ref("hr_expense_sheet.mt_expense_reset")
            case "cancel":
                return self.env.ref("hr_expense_sheet.mt_expense_refused")
            case "paid":
                return self.env.ref("hr_expense_sheet.mt_expense_paid")
            case "approved":
                if init_values["state"] in {
                    "posted",
                    "in_payment",
                    "paid",
                }:  # Reverting state
                    subtype = (
                        "hr_expense_sheet.mt_expense_entry_draft"
                        if self.account_move_ids
                        else "hr_expense_sheet.mt_expense_entry_delete"
                    )
                    return self.env.ref(subtype)
                return self.env.ref("hr_expense_sheet.mt_expense_approved")
            case _:
                return super()._track_subtype(init_values)

    def _message_auto_subscribe_followers(self, updated_values, subtype_ids):
        # Similar to what happens in hr.expense
        res = super()._message_auto_subscribe_followers(updated_values, subtype_ids)
        if updated_values.get("employee_id"):
            employee_user = (
                self.env["hr.employee"].browse(updated_values["employee_id"]).user_id
            )
            if employee_user:
                res.append((employee_user.partner_id.id, subtype_ids, False))
        return res

    def activity_update(self):
        # Similar to what happens in hr.expense
        reports_requiring_feedback = self.env["hr.expense.sheet"]
        reports_activity_unlink = self.env["hr.expense.sheet"]
        for expense_report in self:
            if expense_report.state == "submitted":
                expense_report.activity_schedule(
                    "hr_expense_sheet.mail_act_expense_approval",
                    user_id=expense_report.sudo()
                    ._get_default_responsible_for_approval()
                    .id
                    or self.env.user.id,
                )
            elif expense_report.state == "approved":
                reports_requiring_feedback |= expense_report
            elif expense_report.state in {"draft", "refused"}:
                reports_activity_unlink |= expense_report
        if reports_requiring_feedback:
            reports_requiring_feedback.activity_feedback(
                ["hr_expense_sheet.mail_act_expense_approval"]
            )
        if reports_activity_unlink:
            reports_activity_unlink.activity_unlink(
                ["hr_expense_sheet.mail_act_expense_approval"]
            )

    # --------------------------------------------
    # Actions
    # --------------------------------------------

    def action_submit(self):
        sheets = self.filtered(lambda x: x.state == "draft")
        sheets.approval_state = "submitted"
        for sheet in sheets.filtered(lambda x: not x.manager_id):
            expense = sheet.expense_line_ids[0]
            sheet.manager_id = expense._get_default_responsible_for_approval()
        sheets.expense_line_ids.action_submit()
        sheets.sudo().activity_update()

    def action_approve(self):
        sheets = self.filtered(lambda x: x.state == "submitted")
        res = sheets.expense_line_ids.action_approve()
        if res:
            return res  # duplicate wizard
        for sheet in sheets:
            sheet.write(
                {
                    "approval_state": "approved",
                    "manager_id": sheet.manager_id.id or self.env.user.id,
                    "approval_date": fields.Date.context_today(sheet),
                }
            )
        sheets.sudo().activity_update()

    def action_refuse(self):
        expenses = self.expense_line_ids
        action = expenses.action_refuse()
        action["context"] = {"active_ids": expenses.ids}
        return action

    def _do_refuse(self, reason):
        self.approval_state = "refused"

    def _geet_default_accounting_date(self):
        """
        Calculate the default accounting date for the expenses paid by employees
        """
        self.ensure_one()
        today = fields.Date.context_today(self)
        start_month = fields.Date.start_of(today, "month")
        end_month = fields.Date.end_of(today, "month")
        most_recent_expense = max(
            self.expense_line_ids.filtered(lambda exp: exp.date).mapped("date"),
            default=today,
        )
        if most_recent_expense > end_month:
            return most_recent_expense
        if most_recent_expense >= start_month:
            return today
        lock_date = self.company_id._get_user_fiscal_lock_date(self.journal_id)
        return min(
            max(
                fields.Date.end_of(most_recent_expense, "month"),
                fields.Date.end_of(fields.Date.add(lock_date, months=1), "month"),
            ),
            today,
        )

    def action_post(self):
        sheets = self.filtered(lambda x: x.state == "approved")
        for sheet in sheets.filtered(
            lambda x: x.payment_mode == "own_account" and not x.accounting_date
        ):
            sheet.accounting_date = sheet._geet_default_accounting_date()
        sheets._do_create_moves()

    def action_reset(self):
        self.expense_line_ids.action_reset()
        self._do_reset_approval()

    def action_open_expense_view(self):
        self.ensure_one()
        return self.expense_line_ids._get_records_action(name=self.env_("Expenses"))

    def action_open_account_moves(self):
        self.ensure_one()
        record = (
            self.account_move_ids
            if self.payment_mode == "own_account"
            else self.account_move_ids.origin_payment_id
        )
        return record._get_records_action()

    # --------------------------------------------
    # Business
    # --------------------------------------------

    def _do_reset_approval(self):
        # Similar to what happens in hr.expense
        self.sudo().write(
            {
                "approval_state": False,
                "approval_date": False,
                "accounting_date": False,
                "account_move_ids": [Command.clear()],
            }
        )
        self.activity_update()

    def _do_create_moves(self):
        res = self.expense_line_ids.action_post()
        if res:
            vals = (
                {"accounting_date": self.accounting_date}
                if self.accounting_date
                else {}
            )
            wizard_model = self.env[res["res_model"]].with_context(**res["context"])
            wizard = wizard_model.create(vals)
            wizard.action_post_entry()

    def _get_default_responsible_for_approval(self):
        # Similar to what happens in hr.expense
        self.ensure_one()
        expense = self.expense_line_ids[:1]
        return expense._get_default_responsible_for_approval()
