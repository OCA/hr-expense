# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round


class HrExpense(models.Model):
    _inherit = "hr.expense"

    sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        string="Expense Report",
        domain="[('employee_id', '=', employee_id), ('company_id', '=', company_id)]",
        readonly=True,
        copy=False,
        index=True,
    )
    approval_date = fields.Datetime(compute="_compute_approval_date", store=True)
    journal_id = fields.Many2one(compute="_compute_journal_id", store=True)
    employee_id = fields.Many2one(inverse="_inverse_employee_id")

    @api.depends("sheet_id.department_id", "sheet_id.manager_id")
    def _compute_from_employee_id(self):
        _self = self.filtered(lambda x: x.sheet_id)
        res = super(HrExpense, (self - _self))._compute_from_employee_id()
        for expense in _self:
            expense.department_id = expense.sheet_id.department_id
            expense.manager_id = expense.sheet_id.manager_id
        return res

    @api.depends("sheet_id.is_editable")
    def _compute_is_editable(self):
        _self = self.filtered(lambda x: x.sheet_id)
        res = super(HrExpense, (self - _self))._compute_is_editable()
        for expense in _self:
            expense.is_editable = (
                expense.sheet_id.is_editable if expense.sheet_id else True
            )
        return res

    @api.depends("sheet_id.approval_date")
    def _compute_approval_date(self):
        for expense in self.filtered(lambda x: x.sheet_id):
            expense.approval_date = expense.sheet_id.approval_date

    @api.depends("sheet_id.journal_id", "payment_method_line_id.journal_id")
    def _compute_journal_id(self):
        for expense in self:
            expense.journal_id = (
                expense.sheet_id.journal_id
                if expense.sheet_id
                else expense.payment_method_line_id.journal_id
            )

    @api.depends("sheet_id.payment_method_line_id")
    def _compute_payment_method_line_id(self):
        _self = self.filtered(lambda x: x.sheet_id)
        res = super(HrExpense, (self - _self))._compute_payment_method_line_id()
        for expense in _self:
            expense.payment_method_line_id = expense.sheet_id.payment_method_line_id
        return res

    def _inverse_employee_id(self):
        # In case expense has sheet which has only one expense_line_ids,
        # then changing the expense.employee_id triggers changing the
        # sheet.employee_id too.
        # Otherwise we unlink the expense line from sheet, (so that the user can
        # create a new report).
        for item in self.filtered(lambda x: x.sheet_id):
            employees = item.sheet_id.expense_line_ids.mapped("employee_id")
            if len(employees) == 1:
                item.sheet_id.employee_id = item.employee_id
            elif len(employees) > 1:
                item.sheet_id = False

    @api.constrains("payment_mode")
    def _check_payment_mode(self):
        self.sheet_id._check_payment_mode()

    def _can_be_autovalidated(self):
        res = super()._can_be_autovalidated()
        if self.sheet_id:
            res = bool(res and self.sheet_id.manager_id)
        return res

    def _do_refuse(self, reason):
        res = super()._do_refuse(reason)
        sheets = self.sheet_id
        sheets._do_refuse(reason)
        return res

    def write(self, vals):
        expense_to_previous_sheet = {}
        if "sheet_id" in vals:
            # Store the previous sheet of the expenses to unlink the attachments later
            # if needed
            for expense in self:
                expense_to_previous_sheet[expense] = expense.sheet_id
        res = super().write(vals)
        if "sheet_id" in vals:
            # The sheet_id has been modified, either by an explicit write on
            # sheet_id of the expense,
            # or by processing a command on the sheet's expense_line_ids.
            # We need to delete the attachments on the previous sheet coming
            # from the expenses that were modified,
            # and copy the attachments of the expenses to the new sheet,
            # if it's a no-op (writing same sheet_id as the current sheet_id
            # of the expense),
            # nothing should be done (no unlink then copy of the same attachments)
            attachments_to_unlink = self.env["ir.attachment"]
            for expense in self:
                previous_sheet = expense_to_previous_sheet[expense]
                checksums = set(
                    (
                        expense.attachment_ids
                        - previous_sheet.expense_line_ids.attachment_ids
                    ).mapped("checksum")
                )
                attachments_to_unlink += previous_sheet.attachment_ids.filtered(
                    lambda att, checksums=checksums: att.checksum in checksums
                )
                if vals["sheet_id"] and expense.sheet_id != previous_sheet:
                    for attachment in expense.attachment_ids:
                        attachment.copy(
                            {
                                "res_model": "hr.expense.sheet",
                                "res_id": vals["sheet_id"],
                            }
                        )
            attachments_to_unlink.unlink()
        return res

    def unlink(self):
        attachments_to_unlink = self.env["ir.attachment"]
        for sheet in self.sheet_id:
            expenses = sheet.expense_line_ids.filtered(lambda x: x in self)
            checksums = set(
                (expenses.attachment_ids & self.attachment_ids).mapped("checksum")
            )
            attachments_to_unlink += sheet.attachment_ids.filtered(
                lambda att, checksums=checksums: att.checksum in checksums
            )
        attachments_to_unlink.unlink()
        return super().unlink()

    def action_show_same_receipt_expense_ids(self):
        self.ensure_one()
        return self.same_receipt_expense_ids._get_records_action(
            name=self.env._(
                "Expenses with a similar receipt to %(other_expense_name)s",
                other_expense_name=self.name,
            ),
        )

    def action_view_sheet(self):
        self.ensure_one()
        return self.sheet_id._get_records_action()

    def _check_can_create_sheets(self, expenses):
        if not expenses:
            raise UserError(
                self.env._("You cannot report the expenses without amount!")
            )
        if any(expense.state != "draft" or expense.sheet_id for expense in expenses):
            raise UserError(self.env._("You cannot report twice the same line!"))
        if len(expenses.mapped("employee_id")) != 1:
            raise UserError(
                self.env._(
                    "You cannot report expenses for different employees in the same "
                    "report."
                )
            )
        if any(not expense.product_id for expense in expenses):
            raise UserError(self.env._("You can not create report without category."))
        if len(self.company_id) != 1:
            raise UserError(
                self.env._(
                    "You cannot report expenses for different companies in the same "
                    "report."
                )
            )

    def _prepare_expense_sheet_values(self, expenses):
        # Check if two reports should be created
        own_expenses = expenses.filtered(lambda x: x.payment_mode == "own_account")
        company_expenses = expenses - own_expenses
        create_two_reports = own_expenses and company_expenses
        sheets = (own_expenses, company_expenses) if create_two_reports else (expenses,)
        values = []
        # We use a fallback name only when several expense sheets are created,
        # else we use the form view required name to force the user to set a name
        for todo in sheets:
            paid_by = (
                "company" if todo[0].payment_mode == "company_account" else "employee"
            )
            sheet_name = self.env["hr.expense.sheet"]._get_default_sheet_name(todo)
            if not sheet_name and len(sheets) > 1:
                sheet_name = self.env._(
                    "New Expense Report, paid by %(paid_by)s", paid_by=paid_by
                )
            values.append(
                {
                    "company_id": self.company_id.id,
                    "employee_id": self[0].employee_id.id,
                    "name": sheet_name or "/",
                    "expense_line_ids": [Command.set(todo.ids)],
                    "state": "draft",
                }
            )
        return values

    def get_expenses_to_submit(self):
        # if there ere no records selected, then select all draft expenses for the user
        if self:
            expenses = self.filtered(
                lambda expense: expense.state == "draft"
                and not expense.sheet_id
                and expense.is_editable
            )
        else:
            expenses = (
                self.env["hr.expense"]
                .search(
                    [
                        ("state", "=", "draft"),
                        ("sheet_id", "=", False),
                        ("employee_id", "=", self.env.user.employee_id.id),
                    ]
                )
                .filtered(lambda expense: expense.is_editable)
            )

        if not expenses:
            raise UserError(self.env._("You have no expense to report"))
        return expenses.action_submit_expenses()

    def _create_sheets_from_expense(self):
        if any(not expense.is_editable for expense in self):
            raise UserError(self.env._("You are not authorized to edit this expense."))
        # If there is an expense with total_amount == 0, it means that expense has
        # not been processed by OCR yet
        expenses_with_amount = self.filtered(
            lambda expense: not (
                expense.currency_id.is_zero(expense.total_amount_currency)
                or expense.company_currency_id.is_zero(expense.total_amount)
                or (
                    expense.product_id
                    and not float_round(
                        expense.quantity,
                        precision_rounding=expense.product_uom_id.rounding,
                    )
                )
            )
        )
        self._check_can_create_sheets(expenses_with_amount)
        return self.env["hr.expense.sheet"].create(
            self._prepare_expense_sheet_values(expenses_with_amount)
        )

    def action_submit_expenses(self):
        sheets = self._create_sheets_from_expense()
        return sheets._get_records_action(
            name=self.env._("New Expense Reports"),
        )

    def _prepare_move_vals(self):
        vals = super()._prepare_move_vals()
        vals["expense_sheet_id"] = self.sheet_id.id
        return vals

    def action_get_attachment_view(self):
        self.ensure_one()
        res = self.env["ir.actions.act_window"]._for_xml_id("base.action_attachment")
        res.update(
            {
                "domain": [
                    ("res_model", "=", "hr.expense"),
                    ("res_id", "in", self.ids),
                ],
                "context": {
                    "default_res_model": "hr.expense",
                    "default_res_id": self.id,
                },
            }
        )
        return res

    def update_activities_and_mails(self):
        # We're not calling the super on purpose because we'll be tracking everything
        # in the expense sheet.
        self = self.filtered(lambda x: not x.sheet_id)
        return super().update_activities_and_mails()

    def _track_subtype(self, init_values):
        # We're not calling the super on purpose because we'll be tracking everything
        # in the expense sheet.
        if "state" in init_values:
            return False
        return super()._track_subtype(init_values)
