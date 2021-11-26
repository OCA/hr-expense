# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare
from odoo.tools.safe_eval import safe_eval


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    advance = fields.Boolean(
        string="Employee Advance", compute="_compute_advance", store=True
    )
    advance_sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        string="Clear Advance",
        domain="[('advance', '=', True), ('employee_id', '=', employee_id),"
        " ('clearing_residual', '>', 0.0)]",
        readonly=True,
        states={
            "draft": [("readonly", False)],
            "submit": [("readonly", False)],
            "approve": [("readonly", False)],
        },
        help="Show remaining advance of this employee",
    )
    clearing_sheet_ids = fields.One2many(
        comodel_name="hr.expense.sheet",
        inverse_name="advance_sheet_id",
        string="Clearing Sheet",
        readonly=True,
        help="Show reference clearing on advance",
    )
    clearing_residual = fields.Monetary(
        string="Amount to clear",
        compute="_compute_clearing_residual",
        store=True,
        help="Amount to clear of this expense sheet in company currency",
    )
    advance_sheet_residual = fields.Monetary(
        string="Advance Remaining",
        related="advance_sheet_id.clearing_residual",
        store=True,
        help="Remaining amount to clear the selected advance sheet",
    )
    amount_payable = fields.Monetary(
        string="Payable Amount",
        compute="_compute_amount_payable",
        help="Final regiter payment amount even after advance clearing",
    )

    @api.depends("expense_line_ids")
    def _compute_advance(self):
        for sheet in self:
            if sheet.expense_line_ids:
                sheet.advance = all(sheet.expense_line_ids.mapped("advance"))
            else:
                sheet.advance = self.env.context.get("default_advance", sheet.advance)
        return

    @api.constrains("advance_sheet_id", "expense_line_ids")
    def _check_advance_expense(self):
        advance_lines = self.expense_line_ids.filtered("advance")
        if self.advance_sheet_id and advance_lines:
            raise ValidationError(
                _("Advance clearing must not contain any advance expense line")
            )
        if advance_lines and len(advance_lines) != len(self.expense_line_ids):
            raise ValidationError(_("Advance must contain only advance expense line"))

    @api.depends("account_move_id.line_ids.amount_residual")
    def _compute_clearing_residual(self):
        emp_advance = self.env.ref(
            "hr_expense_advance_clearing.product_emp_advance", False
        )
        for sheet in self:
            residual_company = 0.0
            if emp_advance:
                for line in sheet.sudo().account_move_id.line_ids:
                    if line.account_id == emp_advance.property_account_expense_id:
                        residual_company += line.amount_residual
            sheet.clearing_residual = residual_company

    def _compute_amount_payable(self):
        for sheet in self:
            rec_lines = sheet.account_move_id.line_ids.filtered(
                lambda x: x.credit and x.account_id.reconcile and not x.reconciled
            )
            sheet.amount_payable = -sum(rec_lines.mapped("amount_residual"))

    def action_sheet_move_create(self):
        res = super().action_sheet_move_create()
        # Reconcile advance of this sheet with the advance_sheet
        emp_advance = self.env.ref("hr_expense_advance_clearing.product_emp_advance")
        ctx = self._context.copy()
        ctx.update({"skip_account_move_synchronization": True})
        for sheet in self:
            advance_residual = float_compare(
                sheet.advance_sheet_residual,
                sheet.total_amount,
                precision_rounding=sheet.currency_id.rounding,
            )
            move_lines = (
                sheet.account_move_id.line_ids
                | sheet.advance_sheet_id.account_move_id.line_ids
            )
            account_id = emp_advance.property_account_expense_id.id
            adv_move_lines = (
                self.env["account.move.line"]
                .sudo()
                .search(
                    [
                        ("id", "in", move_lines.ids),
                        ("account_id", "=", account_id),
                        ("reconciled", "=", False),
                    ]
                )
            )
            adv_move_lines.with_context(ctx).reconcile()
            # Update state on clearing advance when advance residual > total amount
            if sheet.advance_sheet_id and advance_residual != -1:
                sheet.write({"state": "done"})
        return res

    def open_clear_advance(self):
        self.ensure_one()
        action = self.env.ref(
            "hr_expense_advance_clearing.action_hr_expense_sheet_advance_clearing"
        )
        vals = action.sudo().read()[0]
        context1 = vals.get("context", {})
        if context1:
            context1 = safe_eval(context1)
        context1["default_advance_sheet_id"] = self.id
        context1["default_employee_id"] = self.employee_id.id
        vals["context"] = context1
        return vals

    def get_domain_advance_sheet_expense_line(self):
        return self.advance_sheet_id.expense_line_ids.filtered("clearing_product_id")

    def create_clearing_expense_line(self, line):
        clear_advance = self._prepare_clear_advance(line)
        clearing_line = self.env["hr.expense"].new(clear_advance)
        return clearing_line

    @api.onchange("advance_sheet_id")
    def _onchange_advance_sheet_id(self):
        self.expense_line_ids -= self.expense_line_ids.filtered("av_line_id")
        self.advance_sheet_id.expense_line_ids.sudo().read()  # prefetch
        lines = self.get_domain_advance_sheet_expense_line()
        for line in lines:
            self.expense_line_ids += self.create_clearing_expense_line(line)

    def _prepare_clear_advance(self, line):
        # Prepare the clearing expense
        clear_line_dict = {
            "advance": False,
            "name": False,
            "product_id": line.clearing_product_id.id,
            "clearing_product_id": False,
            "date": fields.Date.context_today(self),
            "account_id": False,
            "state": "draft",
            "product_uom_id": False,
            "av_line_id": line.id,
        }
        clear_line = self.env["hr.expense"].new(clear_line_dict)
        clear_line._compute_from_product_id_company_id()  # Set some vals
        # Prepare the original advance line
        adv_dict = line._convert_to_write(line._cache)
        # remove no update columns
        _fields = line._fields
        del_cols = [k for k in _fields.keys() if _fields[k].type == "one2many"]
        del_cols += list(self.env["mail.thread"]._fields.keys())
        del_cols += list(self.env["mail.activity.mixin"]._fields.keys())
        del_cols += list(clear_line_dict.keys())
        del_cols = list(set(del_cols))
        adv_dict = {k: v for k, v in adv_dict.items() if k not in del_cols}
        # Assign the known value from original advance line
        clear_line.update(adv_dict)
        clearing_dict = clear_line._convert_to_write(clear_line._cache)
        # Convert list of int to [(6, 0, list)]
        clearing_dict = {
            k: isinstance(v, list)
            and all(isinstance(x, int) for x in v)
            and [(6, 0, v)]
            or v
            for k, v in clearing_dict.items()
        }
        return clearing_dict
