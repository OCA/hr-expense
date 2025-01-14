# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    advance = fields.Boolean(
        string="Employee Advance",
    )
    advance_sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        string="Clear Advance",
        domain="[('advance', '=', True), ('employee_id', '=', employee_id),"
        " ('clearing_residual', '>', 0.0)]",
        help="Show remaining advance of this employee",
    )
    clearing_sheet_ids = fields.One2many(
        comodel_name="hr.expense.sheet",
        inverse_name="advance_sheet_id",
        string="Clearing Sheet",
        readonly=True,
        help="Show reference clearing on advance",
    )
    clearing_count = fields.Integer(
        compute="_compute_clearing_count",
    )
    payment_return_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="advance_id",
        string="Payment Return",
        readonly=True,
        help="Show reference return advance on advance",
    )
    return_count = fields.Integer(compute="_compute_return_count")
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

    @api.constrains("advance_sheet_id", "expense_line_ids")
    def _check_advance_expense(self):
        advance_lines = self.expense_line_ids.filtered("advance")
        if self.advance_sheet_id and advance_lines:
            raise ValidationError(
                _("Advance clearing must not contain any advance expense line")
            )
        if advance_lines and len(advance_lines) != len(self.expense_line_ids):
            raise ValidationError(_("Advance must contain only advance expense line"))

    @api.depends("account_move_ids.payment_state", "account_move_ids.amount_residual")
    def _compute_from_account_move_ids(self):
        """After clear advance.
        if amount residual is zero, payment state will change to 'paid'
        """
        res = super()._compute_from_account_move_ids()
        for sheet in self:
            if (
                sheet.advance_sheet_id
                and sheet.account_move_ids.state == "posted"
                and not sheet.amount_residual
            ):
                sheet.payment_state = "paid"
        return res

    def _get_product_advance(self):
        return self.env.ref("hr_expense_advance_clearing.product_emp_advance", False)

    @api.depends("account_move_ids.line_ids.amount_residual")
    def _compute_clearing_residual(self):
        for sheet in self:
            emp_advance = sheet._get_product_advance()
            residual_company = 0.0
            if emp_advance:
                property_account_expense_id = emp_advance.with_company(
                    sheet.company_id
                ).property_account_expense_id
                for line in sheet.sudo().account_move_ids.line_ids:
                    if line.account_id == property_account_expense_id:
                        residual_company += line.amount_residual
            sheet.clearing_residual = residual_company

    def _compute_amount_payable(self):
        for sheet in self:
            rec_lines = sheet.account_move_ids.line_ids.filtered(
                lambda x: x.credit and x.account_id.reconcile and not x.reconciled
            )
            sheet.amount_payable = -sum(rec_lines.mapped("amount_residual"))

    @api.depends("clearing_sheet_ids")
    def _compute_clearing_count(self):
        for sheet in self:
            sheet.clearing_count = len(sheet.clearing_sheet_ids)

    @api.depends("payment_return_ids")
    def _compute_return_count(self):
        for sheet in self:
            sheet.return_count = len(sheet.payment_return_ids)

    def action_sheet_move_post(self):
        """Post journal entries with clearing document"""
        res = super().action_sheet_move_post()
        for sheet in self:
            if not sheet.advance_sheet_id:
                continue
            amount_residual_bf_reconcile = sheet.advance_sheet_residual
            advance_residual = float_compare(
                amount_residual_bf_reconcile,
                sheet.total_amount,
                precision_rounding=sheet.currency_id.rounding,
            )
            move_lines = (
                sheet.account_move_ids.line_ids
                | sheet.advance_sheet_id.account_move_ids.line_ids
            )
            emp_advance = sheet._get_product_advance()
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
            adv_move_lines.reconcile()
            # Update state on clearing advance when advance residual > total amount
            if advance_residual != -1:
                sheet.write(
                    {
                        "state": "done",
                    }
                )
            # Update amount residual and state when advance residual < total amount
            else:
                sheet.write(
                    {
                        "state": "post",
                        "payment_state": "not_paid",
                        "amount_residual": sheet.total_amount
                        - amount_residual_bf_reconcile,
                    }
                )
        return res

    def _get_move_line_vals(self):
        self.ensure_one()
        move_line_vals = []
        advance_to_clear = self.advance_sheet_residual
        emp_advance = self._get_product_advance()
        account_advance = emp_advance.property_account_expense_id
        for expense in self.expense_line_ids:
            move_line_name = (
                f"{expense.employee_id.name}: {expense.name.splitlines()[0][:64]}"
            )
            partner_id = expense.employee_id.sudo().work_contact_id.id

            total_amount = -expense.total_amount
            total_amount_currency = -expense.total_amount_currency

            # Source move line
            move_line_src = expense._get_move_line_src(move_line_name, partner_id)
            move_line_values = [move_line_src]

            # Destination move line
            move_line_dst = expense._get_move_line_dst(
                move_line_name,
                partner_id,
                total_amount,
                total_amount_currency,
                account_advance,
            )

            # Check clearing > advance, it will split line
            credit = move_line_dst["credit"]
            # cr payable -> cr advance
            remain_payable = 0.0
            payable_move_line = []
            rounding = expense.currency_id.rounding
            if (
                float_compare(
                    credit,
                    advance_to_clear,
                    precision_rounding=rounding,
                )
                == 1
            ):
                remain_payable = credit - advance_to_clear
                move_line_dst.update(
                    {"credit": advance_to_clear, "amount_currency": -advance_to_clear}
                )
                advance_to_clear = 0.0
                # extra payable line
                account_dest = expense.sheet_id._get_expense_account_destination()
                payable_move_line = move_line_dst.copy()
                payable_move_line.update(
                    {
                        "credit": remain_payable,
                        "amount_currency": -remain_payable,
                        "account_id": account_dest,
                    }
                )
            else:
                advance_to_clear -= credit  # Reduce remaining advance

            # Add destination first (if credit is not zero)
            if not float_is_zero(move_line_dst["credit"], precision_rounding=rounding):
                move_line_values.append(move_line_dst)
            if payable_move_line:
                move_line_values.append(payable_move_line)
            move_line_vals.extend(move_line_values)
        return move_line_vals

    def _prepare_bills_vals(self):
        """create journal entry instead of bills when clearing document"""
        self.ensure_one()
        res = super()._prepare_bills_vals()
        if self.advance_sheet_id and self.payment_mode == "own_account":
            # Advance Sheets with no residual left
            if self.advance_sheet_residual <= 0.0:
                raise ValidationError(
                    self.env._(f"Advance: {self.name} has no amount to clear")
                )
            res.update(
                {
                    "move_type": "entry",
                    "line_ids": [
                        Command.create(vals) for vals in self._get_move_line_vals()
                    ],
                }
            )
        return res

    def open_clear_advance(self):
        self.ensure_one()
        result = self.env["ir.actions.act_window"]._for_xml_id(
            "hr_expense_advance_clearing.action_hr_expense_sheet_advance_clearing"
        )
        # Add default context
        context = ast.literal_eval(result["context"])
        context.update(
            {
                "default_advance_sheet_id": self.id,
                "default_employee_id": self.employee_id.id,
            }
        )
        result["context"] = context
        return result

    def get_domain_advance_sheet_expense_line(self):
        return self.advance_sheet_id.expense_line_ids.filtered("clearing_product_id")

    def create_clearing_expense_line(self, line):
        clear_advance = self._prepare_clear_advance(line)
        clearing_line = self.env["hr.expense"].new(clear_advance)
        return clearing_line

    @api.onchange("advance_sheet_id")
    def _onchange_advance_sheet_id(self):
        self.expense_line_ids = self.expense_line_ids.filtered(
            lambda line: not line.av_line_id
        )
        if not self.advance_sheet_id:
            return

        self.advance_sheet_id.expense_line_ids.sudo().read(["id"])
        lines = self.get_domain_advance_sheet_expense_line()
        for line in lines:
            self.expense_line_ids += self.create_clearing_expense_line(line)

    def _prepare_clear_advance(self, line):
        # Prepare the clearing expense
        clear_line_dict = {
            "advance": False,
            "name": line.clearing_product_id.display_name,
            "product_id": line.clearing_product_id.id,
            "clearing_product_id": False,
            "date": fields.Date.context_today(self),
            "account_id": False,
            "state": "draft",
            "product_uom_id": False,
            "av_line_id": line.id,
        }
        clear_line = self.env["hr.expense"].new(clear_line_dict)
        clear_line._compute_account_id()  # Set some vals
        # Prepare the original advance line
        adv_dict = line._convert_to_write(line._cache)

        # Remove non-updatable fields
        del_cols = set.union(
            {
                k for k, v in line._fields.items() if v.type == "one2many"
            },  # Remove O2M fields
            self.env["mail.thread"]._fields.keys(),  # Remove mail.thread fields
            self.env["mail.activity.mixin"]._fields.keys(),  # Remove activity fields
            clear_line_dict.keys(),  # Remove already assigned fields
        )
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

    def action_open_clearings(self):
        self.ensure_one()
        return {
            "name": _("Clearing Sheets"),
            "type": "ir.actions.act_window",
            "res_model": "hr.expense.sheet",
            "view_mode": "list,form",
            "domain": [("id", "in", self.clearing_sheet_ids.ids)],
        }

    def action_open_payment_return(self):
        self.ensure_one()
        return {
            "name": _("Payment Return"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "view_mode": "list,form",
            "domain": [("id", "in", self.payment_return_ids.ids)],
        }

    def action_register_payment(self):
        action = super().action_register_payment()
        if self.env.context.get("hr_return_advance"):
            action["context"].update(
                {
                    "clearing_sheet_ids": self.clearing_sheet_ids.ids,
                }
            )
        return action
