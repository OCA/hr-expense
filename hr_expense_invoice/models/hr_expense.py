# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2020 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.misc import clean_context


class HrExpense(models.Model):
    _inherit = "hr.expense"

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Vendor Bill",
        domain=[
            ("move_type", "=", "in_invoice"),
            ("state", "=", "posted"),
            ("payment_state", "=", "not_paid"),
            ("invoice_expense_ids", "=", False),
        ],
        copy=False,
    )

    def _prepare_invoice_values(self):
        invoice_lines = [
            Command.create(
                {
                    "product_id": self.product_id.id,
                    "name": self.name,
                    # Odoo considers always the amount taxes included, we need to take
                    # the base amount and quantity = 1
                    "price_unit": self.untaxed_amount_currency,
                    "quantity": 1,
                    "account_id": self.account_id.id,
                    "analytic_distribution": self.analytic_distribution,
                    "tax_ids": [Command.set(self.tax_ids.ids)],
                }
            )
        ]
        return {
            "name": "/",
            "move_type": "in_invoice",
            "invoice_date": self.date,
            "invoice_line_ids": invoice_lines,
            "partner_id": self.vendor_id.id,
        }

    def _prepare_transfers_vals(self):
        vals = []
        for expense in self:
            vals.append(
                {
                    **expense._prepare_move_vals(),
                    "ref": expense.name,
                    "move_type": "entry",
                    "company_id": expense.company_id.id,
                    "line_ids": expense._prepare_transfer_move_lines_vals(),
                }
            )
        return vals

    def _prepare_transfer_move_lines_vals(self):
        self.ensure_one()
        employee_partner = self.employee_id.sudo().work_contact_id
        invoice_partner = self.invoice_id.partner_id
        ap_lines = self.invoice_id.line_ids.filtered(
            lambda x: x.display_type == "payment_term"
        )
        amount_invoice = sum(ap_lines.mapped("credit"))
        return [
            Command.create(
                {
                    "account_id": ap_lines.account_id[:1].id,
                    "partner_id": invoice_partner.id,
                    "debit": amount_invoice,
                }
            ),
            Command.create(
                {
                    "account_id": employee_partner.property_account_payable_id.id,
                    "partner_id": employee_partner.id,
                    "credit": amount_invoice,
                }
            ),
        ]

    def action_expense_create_invoice(self):
        invoice = self.env["account.move"].create(self._prepare_invoice_values())
        attachments = self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "in", self.ids)]
        )
        for attachment in attachments:
            attachment.copy({"res_model": invoice._name, "res_id": invoice.id})
        self.write(
            {
                "invoice_id": invoice.id,
                "quantity": 1,
            }
        )
        if self.payment_mode == "company_account":
            invoice.action_post()
        return True

    @api.constrains("invoice_id", "state", "payment_mode")
    def _check_invoice_id(self):
        for expense in self:  # Only non binding expense
            if expense.state not in ("posted", "in_payment", "paid"):
                continue
            if expense.payment_mode == "company_account":
                continue
            if expense.invoice_id and expense.invoice_id.state != "posted":
                raise UserError(self.env._("Vendor bill state must be Posted"))

    @api.onchange("invoice_id")
    def _onchange_invoice_id(self):
        """Assure quantity is 1 if an invoice is set for having proper totals, and
        the rest of the fields that are not computed writable, avoiding to ud
        """
        if self.invoice_id:
            self.quantity = 1
            self.name = self.name.split(" | ")[0].strip()
            self.name = "{} | {}".format(self.name or "", self.invoice_id.name)
            self.date = self.invoice_id.date
            if self.invoice_id.company_id != self.company_id:
                # for avoiding to trigger dependent computes
                self.company_id = self.invoice_id.company_id.id

    @api.depends("account_move_id.line_ids.reconciled")
    def _compute_state(self):
        expenses_with_invoices = self.filtered(
            lambda x: x.invoice_id and x.account_move_id
        )
        res = super(HrExpense, (self - expenses_with_invoices))._compute_state()
        for expense in expenses_with_invoices:
            move = expense.account_move_id
            vendor_lines = move.line_ids.filtered_domain(
                [
                    ("partner_id", "=", expense.invoice_id.partner_id.id),
                ]
            )
            employee_lines = move.line_ids.filtered_domain(
                [
                    (
                        "partner_id",
                        "=",
                        expense.employee_id.sudo().work_contact_id.id,
                    ),
                ]
            )
            if employee_lines and all(employee_lines.mapped("reconciled")):
                expense.state = "paid"
            elif vendor_lines and all(vendor_lines.mapped("reconciled")):
                expense.state = self.env["account.move"]._get_invoice_in_payment_state()
            else:
                expense.state = "posted"
        return res

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
    @api.depends("invoice_id", "invoice_id.amount_total", "tax_ids")
    def _compute_price_unit(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.price_unit = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_price_unit()

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
    @api.depends("invoice_id", "invoice_id.amount_total", "tax_ids")
    def _compute_total_amount_currency(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.total_amount_currency = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_total_amount_currency()

    @api.depends("invoice_id", "invoice_id.currency_id")
    def _compute_currency_id(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.currency_id = record.invoice_id.currency_id
        return super(HrExpense, self - with_invoice)._compute_currency_id()

    @api.depends("invoice_id")
    def _compute_tax_ids(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.tax_ids = [(5,)]
        return super(HrExpense, self - with_invoice)._compute_tax_ids()

    def _check_can_create_move(self):
        res = super()._check_can_create_move()
        expenses_with_invoices = self.filtered("invoice_id")
        # Check expenses without posted invoices
        if exp_wo_posted_invoices := expenses_with_invoices.filtered_domain(
            [("invoice_id.state", "!=", "posted")]
        ):
            raise UserError(
                self.env._(
                    "You can't create an accounting entry for an expense "
                    "linked to a vendor bill that is not posted.\n"
                    "Please post Vendor Bills of %s and try again.",
                    ", ".join(exp_wo_posted_invoices.mapped("name")),
                )
            )
        return res

    def _reconcile_transfer_moves(self):
        for item in self.filtered("invoice_id"):
            # All transfer moves should be posted
            vendor_inv_lines = item.invoice_id.line_ids.filtered_domain(
                [
                    ("display_type", "=", "payment_term"),
                ]
            )
            vendor_transfer_lines = item.account_move_id.line_ids.filtered_domain(
                [
                    ("partner_id", "=", item.invoice_id.partner_id.id),
                ]
            )
            if vendor_inv_lines and vendor_transfer_lines:
                (vendor_inv_lines + vendor_transfer_lines).reconcile()

    def _do_reset_approval(self):
        self.sudo().write({"invoice_id": False})
        return super()._do_reset_approval()

    def action_reset(self):
        self = self.with_context(clean_context(self.env.context))  # pylint: disable=W8121
        # Invoices
        invoices_sudo = self.sudo().invoice_id
        draft_invoices_sudo = invoices_sudo.filtered(lambda m: m.state == "draft")
        non_draft_invoices_sudo = invoices_sudo - draft_invoices_sudo
        non_draft_invoices_sudo._reverse_moves(
            default_values_list=[
                {"invoice_date": fields.Date.context_today(inv_sudo)}
                for inv_sudo in non_draft_invoices_sudo
            ],
            cancel=True,
        )
        draft_invoices_sudo.unlink()
        return super().action_reset()
