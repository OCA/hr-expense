# Copyright 2017 Tecnativa - Vicent Cubells
# Copyright 2020 Tecnativa - David Vidal
# Copyright 2021 Tecnativa - Víctor Martínez
# Copyright 2015-2024 Tecnativa - Pedro M. Baeza
# Copyright 2026 Moduon - Eduardo de Miguel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models
from odoo.exceptions import RedirectWarning, UserError
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
    transfer_move_ids = fields.One2many(
        comodel_name="account.move",
        inverse_name="source_invoice_expense_id",
    )
    # This field has been added to reintroduce tracking for the amount due on each
    # expense, a feature that existed in previous versions. The tracking is necessary
    # to accurately reflect the payment state of the expense sheet.
    amount_residual = fields.Monetary(
        string="Amount Due", compute="_compute_amount_residual", store=True
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

    def _prepare_own_account_transfer_move_vals(self):
        self.ensure_one()
        self = self.with_company(self.company_id)
        # TODO: Allow to select a specific journal
        journal = self.env["account.journal"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("type", "=", "general"),
            ],
            limit=1,
        )
        employee_partner = self.employee_id.sudo().work_contact_id
        invoice_partner = self.invoice_id.partner_id
        ap_lines = self.invoice_id.line_ids.filtered(
            lambda x: x.display_type == "payment_term"
        )
        amount_invoice = sum(ap_lines.mapped("credit"))
        return {
            "journal_id": journal.id,
            "move_type": "entry",
            "name": "/",
            "date": self.date,
            "ref": self.name,
            "source_invoice_expense_id": self.id,
            "line_ids": [
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
            ],
        }

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
                "tax_ids": False,
                "price_unit": invoice.amount_total,
            }
        )
        if self.payment_mode == "company_account":
            invoice.action_post()
        return True

    def action_view_invoice(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "name": self.invoice_id.name,
            "view_mode": "form",
            "res_id": self.invoice_id.id,
            "views": [(self.env.ref("account.view_move_form").id, "form")],
            "target": "current",
        }

    def action_view_transfer_moves(self):
        self.ensure_one()
        action_name = self.env._("Transfer of %s", self.name)
        if len(self.transfer_move_ids) == 1:
            return {
                "type": "ir.actions.act_window",
                "res_model": "account.move",
                "name": action_name,
                "view_mode": "form",
                "res_id": self.transfer_move_ids.id,
                "views": [(self.env.ref("account.view_move_form").id, "form")],
                "target": "current",
            }
        # Multiple transfer moves
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "account.action_move_journal_line"
        )
        action["name"] = action_name
        action["domain"] = [("id", "in", self.transfer_move_ids.ids)]
        return action

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

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
    @api.depends("invoice_id", "tax_ids")
    def _compute_price_unit(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.price_unit = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_price_unit()

    # tax_ids put as dependency for assuring this is computed after setting tax_ids
    @api.depends("invoice_id", "tax_ids")
    def _compute_total_amount_currency(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.total_amount_currency = record.invoice_id.amount_total
        return super(HrExpense, self - with_invoice)._compute_total_amount_currency()

    @api.depends("invoice_id")
    def _compute_currency_id(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.currency_id = record.invoice_id.currency_id.id
        return super(HrExpense, self - with_invoice)._compute_currency_id()

    @api.depends("invoice_id")
    def _compute_tax_ids(self):
        with_invoice = self.filtered("invoice_id")
        for record in with_invoice:
            record.tax_ids = [(5,)]
        return super(HrExpense, self - with_invoice)._compute_tax_ids()

    @api.depends(
        "transfer_move_ids.line_ids.amount_residual",
        "transfer_move_ids.line_ids.amount_residual_currency",
    )
    def _compute_amount_residual(self):
        """Compute the amount residual for expenses paid by employee with invoices."""
        for rec in self:
            if not rec.currency_id or rec.currency_id == rec.company_currency_id:
                residual_field = "amount_residual"
            else:
                residual_field = "amount_residual_currency"
            payment_term_lines = rec.transfer_move_ids.sudo().line_ids.filtered(
                lambda x: x.account_type in ("asset_receivable", "liability_payable")
            )
            rec.amount_residual = -sum(payment_term_lines.mapped(residual_field))

    def _check_can_create_move(self):
        res = super()._check_can_create_move()
        expenses_with_invoices = self.filtered("invoice_id")
        # Check expeneses with transfer moves
        if exp_w_tranfers := expenses_with_invoices.filtered_domain(
            [("transfer_move_ids", "!=", False)]
        ):
            raise UserError(
                self.env._(
                    "You can't create an accounting entry for an expense "
                    "already linked to a transfer journal entry.\n"
                    "Please unselect %s and try again.",
                    ", ".join(exp_w_tranfers.mapped("name")),
                )
            )
        # Check expeneses without posted invoices
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
        # Check expeneses without employee work email
        if emp_wo_email := expenses_with_invoices.employee_id.filtered_domain(
            [
                ("work_email", "=", False),
            ]
        ):
            action = self.env["ir.actions.actions"]._for_xml_id(
                "hr.open_view_employee_list_my"
            )
            action["domain"] = [("id", "in", emp_wo_email.ids)]
            raise RedirectWarning(
                self.env._(
                    "The work email of some employees is missing.\n"
                    "Please add it on the employee form."
                ),
                action,
                self.env._("Show missing work email employees"),
            )
        return res

    def _reconcile_transfer_moves(self):
        # Reconcile transfer entries with vendor bills once they are posted
        self.ensure_one()
        if self.payment_mode != "own_account":
            return
        if not self.invoice_id or not self.transfer_move_ids:
            raise UserError(
                self.env._(
                    "You can't reconcile an expense linked to a "
                    "Vendor Bill or Transfer that doesn't exist (%s).",
                    self.name,
                )
            )
        # All transfer moves should be posted
        vendor_inv_lines = self.invoice_id.line_ids.filtered_domain(
            [
                ("display_type", "=", "payment_term"),
            ]
        )
        vendor_transfer_lines = self.transfer_move_ids.line_ids.filtered_domain(
            [
                ("partner_id", "=", self.invoice_id.partner_id.id),
            ]
        )
        if vendor_inv_lines and vendor_transfer_lines:
            (vendor_inv_lines + vendor_transfer_lines).reconcile()

    def _action_expense_create_transfer_moves(self):
        for expense in self:
            transfer_move_vals = expense._prepare_own_account_transfer_move_vals()
            transfer_move = self.env["account.move"].create(transfer_move_vals)
            transfer_move.action_post()
            expense._reconcile_transfer_moves()

    def action_post(self):
        self._check_can_create_move()
        expenses_with_invoices = self.filtered("invoice_id")
        expenses_with_invoices._action_expense_create_transfer_moves()
        if expenses_without_invoices := self - expenses_with_invoices:
            return super(HrExpense, expenses_without_invoices).action_post()
        return

    @api.depends("invoice_id.state", "transfer_move_ids.line_ids.reconciled")
    def _compute_state(self):
        expenses_with_invoices = self.filtered("invoice_id")
        if expenses_without_invoices := self - expenses_with_invoices:
            super(HrExpense, expenses_without_invoices)._compute_state()

        for expense in expenses_with_invoices:
            bill = expense.invoice_id
            transfers = expense.transfer_move_ids
            employee_parnter = expense.employee_id.sudo().work_contact_id
            # Shortcut to paid, as it's already paid,
            # but we may not have the bank statement yet
            if expense.payment_mode == "company_account":
                expense.state = "paid"
            # Check state of vendor bills
            elif bill.state == "cancel":
                # Nothing to do with the expense
                expense.state = "paid"
            elif bill.state == "draft" or not transfers:
                # Bill created, and not posted yet
                # No transfer moves, so need to be able to create
                expense.state = "approved"
            elif bill.payment_state == "not_paid":
                # Transfers are created and bill is posted, but not reconciled
                # They should reconcile manually with the transfer moves
                expense.state = "posted"
            elif bill.payment_state in ("partial", "in_payment", "paid", "reversed"):
                # All vendor move lines are reconciled: in_payment
                vendor_transfer_lines = transfers.line_ids.filtered_domain(
                    [
                        ("partner_id", "=", bill.partner_id.id),
                    ]
                )
                if all(vendor_transfer_lines.mapped("reconciled")):
                    expense.state = "in_payment"
                # All employee move lines are reconciled: paid
                employee_transfer_lines = transfers.line_ids.filtered_domain(
                    [
                        ("partner_id", "=", employee_parnter.id),
                    ]
                )
                if all(employee_transfer_lines.mapped("reconciled")):
                    expense.state = "paid"
            else:
                expense.state = expense.approval_state or "draft"
        return

    def _check_can_reset_approval(self):
        expenses_with_invoices = self.filtered("invoice_id")
        res = super(
            HrExpense, self - expenses_with_invoices
        )._check_can_reset_approval()
        if not all(self.mapped("can_reset")):
            raise UserError(
                self.env._(
                    "Only HR Officers, accountants, "
                    "or the concerned employee can reset to draft."
                )
            )
        if any(
            state not in {False, "draft"}
            for state in expenses_with_invoices.invoice_id.mapped("state")
        ):
            raise UserError(
                self.env._(
                    "You cannot reset to draft an "
                    "expense linked to a posted journal entry."
                )
            )
        if any(
            state not in {False, "draft"}
            for state in expenses_with_invoices.transfer_move_ids.mapped("state")
        ):
            raise UserError(
                self.env._(
                    "You cannot reset to draft an "
                    "expense linked to a posted transfer journal entry."
                )
            )
        return res

    def action_reset(self):
        self = self.with_context(**clean_context(self.env.context))
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
        # Trasfers
        transfers_sudo = self.sudo().transfer_move_ids
        draft_transfers_sudo = transfers_sudo.filtered(lambda m: m.state == "draft")
        non_draft_transfers_sudo = transfers_sudo - draft_transfers_sudo
        non_draft_transfers_sudo._reverse_moves(
            default_values_list=[
                {"invoice_date": fields.Date.context_today(transfer_sudo)}
                for transfer_sudo in non_draft_transfers_sudo
            ],
            cancel=True,
        )
        draft_transfers_sudo.unlink()
        return super().action_reset()

    def _do_reset_approval(self):
        self.sudo().write({"invoice_id": False, "transfer_move_ids": []})
        return super()._do_reset_approval()
