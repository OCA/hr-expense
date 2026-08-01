from collections import defaultdict

from odoo import _, fields, models
from odoo.exceptions import UserError


class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    def _is_vendor_bill_sheet(self):
        self.ensure_one()
        return self.payment_mode == "own_account" and bool(
            self.expense_line_ids.filtered("vendor_id")
        )

    def _create_supplier_invoices(self):
        invoices = self.env["account.move"]
        for sheet in self:
            # Agrupar gastos por proveedor
            expenses_by_supplier = defaultdict(list)
            for exp in sheet.expense_line_ids:
                if exp.vendor_id:
                    expenses_by_supplier[exp.vendor_id].append(exp)

            # Para cada proveedor, generar una factura
            for supplier, expenses in expenses_by_supplier.items():
                inv_date = fields.Date.context_today(self)
                invoice_lines = []

                for exp in expenses:
                    # Calcular precio sin impuestos (subtotal) y asignar impuestos
                    net_amount = exp.total_amount - exp.tax_amount
                    invoice_lines.append(
                        (
                            0,
                            0,
                            {
                                "name": exp.name
                                or _("Expense from %s") % supplier.name,
                                "account_id": exp.account_id.id,
                                "quantity": 1.0,
                                "price_unit": net_amount,
                                "tax_ids": [(6, 0, exp.tax_ids.ids)],
                            },
                        )
                    )

                # Encabezado de la factura de proveedor
                inv_vals = {
                    "move_type": "in_invoice",
                    "partner_id": supplier.id,
                    "invoice_date": inv_date,
                    "invoice_date_due": inv_date,
                    "journal_id": sheet.journal_id.id,
                    "ref": _("Expenses %s") % sheet.name,
                    "expense_sheet_id": sheet.id,
                    "invoice_line_ids": invoice_lines,
                    "state": "draft",
                }
                invoice = self.env["account.move"].create(inv_vals)
                invoices |= invoice

        return invoices

    def _generate_supplier_payments(self):
        PaymentRegister = self.env["account.payment.register"]

        for sheet in self:
            pay_journal = self.env["account.journal"].search(
                [
                    ("type", "=", "bank"),
                    ("name", "ilike", "Employee payments"),
                    ("company_id", "=", sheet.company_id.id),
                ],
                limit=1,
            ) or self.env["account.journal"].search(
                [("type", "=", "bank"), ("company_id", "=", sheet.company_id.id)],
                limit=1,
            )
            if not pay_journal:
                raise UserError(
                    _(
                        "Configure at least one bank journal "
                        "to register vendor payments."
                    )
                )

            if pay_journal.outbound_payment_method_line_ids:
                pm_line = pay_journal.outbound_payment_method_line_ids[:1]
            else:
                manual = self.env.ref(
                    "account.account_payment_method_manual_out",
                    raise_if_not_found=False,
                )
                if not manual:
                    raise UserError(
                        _(
                            "Journal '%s' has no payment method "
                            "and the manual method does not exist."
                        )
                        % pay_journal.name
                    )
                pm_line = self.env["account.payment.method.line"].create(
                    {
                        "journal_id": pay_journal.id,
                        "payment_method_id": manual.id,
                        "payment_type": "outbound",
                        "code": manual.code or "manual",
                        "name": manual.name or _("Manual"),
                    }
                )

            employee_contact = sheet.employee_id.sudo().work_contact_id
            invoices_to_pay = sheet.account_move_ids.filtered(
                lambda m, employee_contact=employee_contact: (
                    m.move_type == "in_invoice"
                    and m.partner_id != employee_contact
                    and m.payment_state != "paid"
                )
            )

            for invoice in invoices_to_pay:
                if invoice.amount_residual > 0:
                    context = {
                        "active_model": "account.move",
                        "active_ids": [invoice.id],
                        "active_id": invoice.id,
                    }
                    wizard = PaymentRegister.with_context(**context).create(
                        {
                            "journal_id": pay_journal.id,
                            "payment_method_line_id": pm_line.id,
                            "amount": invoice.amount_residual,
                            "payment_date": fields.Date.context_today(sheet),
                        }
                    )
                    wizard.action_create_payments()

    def _create_employee_reimbursement_invoice(self):
        AccountMove = self.env["account.move"]
        invoices = self.env["account.move"]

        company = self.company_id
        acc_debit = company.hr_expense_reimbursement_debit_account_id
        acc_credit = company.hr_expense_reimbursement_credit_account_id
        if not acc_debit or not acc_credit:
            raise UserError(
                _(
                    "Configure the debit and credit accounts for employee "
                    "reimbursements in Settings > Companies."
                )
            )

        for sheet in self:
            total_amount = sum(exp.total_amount for exp in sheet.expense_line_ids)
            if total_amount <= 0:
                continue

            partner = sheet.employee_id.sudo().work_contact_id
            if not partner:
                raise UserError(
                    _("Employee %s has no work contact configured.")
                    % sheet.employee_id.name
                )
            partner = partner.with_company(sheet.company_id)

            inv_date = fields.Date.context_today(sheet)

            journal = sheet.journal_id
            if not journal:
                raise UserError(_("No journal is defined on the expense sheet."))

            invoice_lines = [
                (
                    0,
                    0,
                    {
                        "name": _("Expense reimbursement"),
                        "account_id": acc_debit.id,
                        "quantity": 1.0,
                        "price_unit": total_amount,
                        "tax_ids": [],
                    },
                )
            ]

            move_vals = {
                "move_type": "in_invoice",
                "partner_id": partner.id,
                "invoice_date": inv_date,
                "invoice_date_due": inv_date,
                "ref": _("Reimbursement %s") % sheet.name,
                "journal_id": journal.id,
                "invoice_line_ids": invoice_lines,
                "state": "draft",
            }

            move = AccountMove.create(move_vals)
            # Don't post the move here - let action_sheet_move_post handle it
            sheet.write({"account_move_ids": [(4, move.id)]})
            invoices |= move

        return invoices

    def _reconcile_account_lines(self):
        for sheet in self:
            account = sheet.company_id.hr_expense_reimbursement_credit_account_id
            if not account:
                raise UserError(
                    _(
                        "Configure the reconciliation account in "
                        "Accounting > Configuration > Companies."
                    )
                )
            move_lines = self.env["account.move.line"].search(
                [
                    ("move_id", "in", sheet.account_move_ids.ids),
                    ("account_id", "=", account.id),
                    ("reconciled", "=", False),
                ]
            )
            if len(move_lines) >= 2:
                move_lines.reconcile()

    def action_approve_expense_sheets(self):
        # Método original para aprobar hojas de gasto
        res = super().action_approve_expense_sheets()

        for sheet in self.filtered(lambda s: s._is_vendor_bill_sheet()):
            moves = sheet.account_move_ids.sudo()
            for move in moves:
                if move.state == "posted":
                    move.sudo().button_cancel()
                    move.sudo().button_draft()
                elif move.state == "cancel":
                    move.sudo().button_draft()
            moves.unlink()
            sheet.sudo().write({"account_move_ids": [(5, 0, 0)]})

            sheet._create_supplier_invoices()
            sheet._create_employee_reimbursement_invoice()
        return res

    def action_sheet_move_post(self):
        # Separate own_account sheets that need custom posting
        own_account_sheets = self.filtered(lambda sheet: sheet._is_vendor_bill_sheet())
        standard_sheets = self - own_account_sheets

        # Handle own_account sheets with custom logic
        for sheet in own_account_sheets:
            # Ensure moves exist (in case method is called without approval)
            if not sheet.account_move_ids:
                raise UserError(
                    _(
                        "There are no journal entries to post. "
                        "Make sure the expense sheet is approved."
                    )
                )

            employee_contact = sheet.employee_id.sudo().work_contact_id
            # Separate employee reimbursement from supplier invoices
            supplier_invoices = sheet.account_move_ids.filtered(
                lambda m, employee_contact=employee_contact: (
                    m.move_type == "in_invoice"
                    and m.state == "draft"
                    and m.partner_id != employee_contact
                )
            )

            employee_reimbursement = sheet.account_move_ids.filtered(
                lambda m, employee_contact=employee_contact: (
                    m.move_type == "in_invoice"
                    and m.state == "draft"
                    and m.partner_id == employee_contact
                )
            )

            # Step 1: Post supplier invoices
            supplier_invoices.action_post()

            # Step 2: Generate payments for posted supplier invoices
            sheet._generate_supplier_payments()

            # Step 3: Post employee reimbursement invoice
            employee_reimbursement.action_post()

            # Step 4: Reconcile everything
            sheet._reconcile_account_lines()

            # Step 5: Change sheet state to done (or final state)
            sheet.write({"state": "done"})

        # Handle standard sheets using parent method
        if standard_sheets:
            super(HrExpenseSheet, standard_sheets).action_sheet_move_post()

        return True

    def action_open_account_moves(self):
        self.ensure_one()
        # Prepara la acción para mostrar los movimientos contables relacionados
        action = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "views": [(False, "list"), (False, "form")],
            "domain": [("id", "in", self.account_move_ids.ids)],
            "context": {"default_expense_sheet_id": self.id},
        }
        # Si solo hay un movimiento, abre directamente el formulario
        if len(self.account_move_ids) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": self.account_move_ids.id,
                }
            )
        return action

    # El metodo borrar los asientos contables al regresar la hoja de gastos a borrador
    def action_reset_expense_sheets(self):
        """
        Override to properly handle accounting entries when resetting to draft.
        This ensures posted journal entries are cancelled and removed.
        """
        sheets_with_moves = self.filtered(
            lambda s: s._is_vendor_bill_sheet() and s.account_move_ids
        )

        if sheets_with_moves:
            for sheet in sheets_with_moves:
                moves = sheet.account_move_ids

                # First: Reset all moves to draft
                for move in moves:
                    if not move:
                        continue

                    # Store move name for audit trail
                    move_name = move.name or "Draft"
                    move_state = move.state

                    # Handle posted moves
                    if move_state == "posted":
                        # In Odoo 18, use button_draft to unpost
                        try:
                            if sheet.payment_mode == "own_account":
                                move.button_draft()
                            else:
                                move.payment_ids.action_draft()

                        except Exception as e:
                            raise UserError(
                                _(
                                    "Cannot reset expense sheet '%(sheet)s'. "
                                    "Failed to unpost journal entry '%(move)s': %(e)s"
                                )
                                % {"sheet": sheet.name, "move": move_name, "e": str(e)}
                            ) from e

                    for move in moves:
                        for line in move.line_ids:
                            if line.matched_debit_ids or line.matched_credit_ids:
                                # Remove reconciliations from debit and credit sides
                                line.matched_debit_ids.unlink()
                                line.matched_credit_ids.unlink()

                # Second: Delete all moves in one action after they're reset to draft
                try:
                    if sheet.payment_mode == "own_account":
                        moves.payment_ids.unlink()
                        moves.unlink()
                    else:
                        moves.payment_ids.unlink()

                except Exception as e:
                    raise UserError(
                        _("Cannot delete journal entries: %s") % str(e)
                    ) from None

                # Clear the reference after processing all moves for this sheet
                sheet.write({"account_move_ids": False})

        # Call parent method to execute original reset logic
        res = super().action_reset_expense_sheets()

        # Additional cleanup: Clear accounting date
        self.write({"accounting_date": False})

        # Post message about reset
        for sheet in self:
            sheet.message_post(
                body=_("Expense sheet has been reset to draft."),
                subject=_("Reset to Draft"),
            )

        return res
