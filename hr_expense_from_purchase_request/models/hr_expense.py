# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    employee_user_id = fields.Many2one(
        related="employee_id.user_id",
        readonly=True,
    )
    purchase_request_id = fields.Many2one(
        comodel_name="purchase.request",
        string="Purchase Request",
        ondelete="restrict",
        domain="[('requested_by', '=', employee_user_id), ('state', '=', 'approved')]",
        readonly=True,
        states={"draft": [("readonly", False)]},
        copy=False,
        index=True,
        help="Select purchase request of this employee, to create expense lines",
    )
    pr_for = fields.Selection(
        selection=[("expense", "Expense")],
        string="Use PR for",
        default="expense",
        required=True,
    )
    pr_line_ids = fields.One2many(
        comodel_name="hr.expense.sheet.prline",
        inverse_name="sheet_id",
        copy=False,
    )
    no_pr_check = fields.Boolean(
        string="Skip Amount Check",
        groups="hr_expense.group_hr_expense_manager",
        copy=False,
    )

    @api.onchange("employee_id")
    def _onchange_purchase_request_employee(self):
        self.purchase_request_id = False

    @api.onchange("purchase_request_id")
    def _onchange_purchase_request_id(self):
        SheetPRLine = self.env["hr.expense.sheet.prline"]
        self.pr_line_ids = False
        for line in self.purchase_request_id.line_ids:
            sheet_prline = self._prepare_sheet_prline(line)
            self.pr_line_ids += SheetPRLine.new(sheet_prline)

    def _prepare_sheet_prline(self, line):
        """ Prepare data, to create hr.expense. All must be hr.expense's fields """
        unit_amount = (
            line.estimated_cost / line.product_qty if line.product_qty > 0 else 0
        )
        return {
            "unit_amount": unit_amount,
            "quantity": line.product_qty,
            "pr_line_id": line.id,
        }

    @api.model
    def create(self, vals):
        sheet = super().create(vals)
        if "purchase_request_id" in vals:
            sheet.mapped("expense_line_ids").filtered("pr_line_id").unlink()
        sheet._do_process_from_purchase_request()
        sheet.pr_line_ids.unlink()  # clean after use
        return sheet

    def write(self, vals):
        res = super().write(vals)
        if "purchase_request_id" in vals:
            self.mapped("expense_line_ids").filtered("pr_line_id").unlink()
        self._do_process_from_purchase_request()
        self.mapped("pr_line_ids").unlink()  # clean after use
        return res

    def _do_process_from_purchase_request(self):
        """ Hook method """
        sheets = self.filtered(lambda l: l.pr_for == "expense")
        sheets._create_expenses_from_prlines()

    def _create_expenses_from_prlines(self):
        for sheet in self:
            expenses_list = []
            sheet.pr_line_ids.read()  # Force prefetch
            for line in sheet.pr_line_ids:
                pr_line = self._prepare_expense_from_prline(line)
                expenses_list.append(pr_line)
            self.env["hr.expense"].sudo().create(expenses_list)

    def _prepare_expense_from_prline(self, line):
        # Read origin prline values with same columns as Expense object
        pr_line = self.env["hr.expense"]._convert_to_write(line.pr_line_id.read()[0])
        # Remove unused fields, i.e., one2many, mail.thread and mail.activity.mixin
        _fields = line.pr_line_id._fields
        del_cols = [k for k in _fields.keys() if _fields[k].type == "one2many"]
        del_cols += list(self.env["mail.thread"]._fields.keys())
        del_cols += list(self.env["mail.activity.mixin"]._fields.keys())
        del_cols = list(set(del_cols))
        pr_line = {k: v for k, v in pr_line.items() if k not in del_cols}
        # sheet_pr_line gets higher priority
        sheet_pr_line = self.env["hr.expense"]._convert_to_write(line._cache)
        pr_line.update(sheet_pr_line)
        # Convert list of int to [(6, 0, list)]
        pr_line = {
            k: isinstance(v, list) and [(6, 0, v)] or v for k, v in pr_line.items()
        }
        return pr_line

    def action_submit_sheet(self):
        for rec in self.filtered("purchase_request_id"):
            pr_amount = sum(rec.purchase_request_id.line_ids.mapped("estimated_cost"))
            ex_amount = sum(rec.expense_line_ids.mapped("untaxed_amount"))
            if not rec.sudo().no_pr_check and ex_amount > pr_amount:
                raise UserError(
                    _(
                        "Requested amount exceed the approved amount from "
                        "purchase request.\nPlease contact your HR manager."
                    )
                )
        return super().action_submit_sheet()

    def approve_expense_sheets(self):
        purchase_requests = self.mapped("purchase_request_id")
        for purchase_request in purchase_requests:
            if purchase_request.state != "approved":
                raise UserError(
                    _(
                        "Purchase Request %s should be in status "
                        "'Approved' when approving this expense"
                    )
                    % purchase_request.name
                )
        purchase_requests.button_done()
        return super().approve_expense_sheets()


class HrExpense(models.Model):
    _inherit = "hr.expense"

    pr_line_id = fields.Many2one(
        comodel_name="purchase.request.line",
        ondelete="cascade",
        help="Expense created from this purchase request line",
    )


class HrExpenseSheetPRLine(models.Model):
    _name = "hr.expense.sheet.prline"
    _description = "Temp Holder of PR Lines data, used to create hr.expense"

    sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        string="Expense Report",
    )
    pr_line_id = fields.Many2one(
        comodel_name="purchase.request.line",
        ondelete="cascade",
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        related="sheet_id.employee_id",
        readonly=True,
    )
    name = fields.Char(
        string="Description",
        related="pr_line_id.name",
        readonly=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        related="pr_line_id.product_id",
        readonly=True,
    )
    quantity = fields.Float(
        string="Quantity",
        digits="Product Unit of Measure",
    )
    total_amount = fields.Monetary(
        string="Total",
        compute="_compute_total_amount",
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        related="pr_line_id.currency_id",
        readonly=True,
    )
    unit_amount = fields.Monetary(
        string="Unit Price",
    )
    description = fields.Text(
        string="Notes...",
    )
    description = fields.Text(
        string="Notes...",
        related="pr_line_id.description",
        readonly=True,
    )
    reference = fields.Text(
        string="Bill Reference",
        related="pr_line_id.specifications",
        readonly=True,
    )

    @api.depends("unit_amount", "quantity")
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.unit_amount * rec.quantity
