# Copyright 2026 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("post_install", "-at_install")
class TestHrExpenseVendorBill(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vendor = cls.env["res.partner"].create({"name": "Test Vendor"})
        cls.company = cls.company_data["company"]
        cls.company.write(
            {
                "hr_expense_reimbursement_debit_account_id": cls.company_data[
                    "default_account_expense"
                ].id,
                "hr_expense_reimbursement_credit_account_id": cls.company_data[
                    "default_account_payable"
                ].id,
            }
        )

    def _create_own_account_sheet(self, total_amount=100.0):
        return self.create_expense_report(
            {
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": total_amount,
                            "vendor_id": self.vendor.id,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )

    def test_vendor_id_on_expense(self):
        expense = self.create_expense({"vendor_id": self.vendor.id})
        self.assertEqual(expense.vendor_id, self.vendor)

    def test_create_supplier_invoices(self):
        sheet = self._create_own_account_sheet()
        invoices = sheet._create_supplier_invoices()
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.partner_id, self.vendor)
        self.assertEqual(invoices.expense_sheet_id, sheet)
        self.assertEqual(invoices.move_type, "in_invoice")

    def test_create_employee_reimbursement_invoice(self):
        sheet = self._create_own_account_sheet(total_amount=250.0)
        invoices = sheet._create_employee_reimbursement_invoice()
        employee_partner = sheet.employee_id.sudo().work_contact_id
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices.partner_id, employee_partner)
        self.assertEqual(invoices.move_type, "in_invoice")
        self.assertIn(sheet, invoices.expense_sheet_id)

    def test_reimbursement_payment_state(self):
        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.expense_employee.work_contact_id.id,
                "is_employee_reimbursement": True,
            }
        )
        move._compute_payment_state()
        self.assertEqual(move.payment_state, "not_paid")

    def test_missing_reimbursement_accounts_raises(self):
        self.company.write(
            {
                "hr_expense_reimbursement_debit_account_id": False,
                "hr_expense_reimbursement_credit_account_id": False,
            }
        )
        sheet = self._create_own_account_sheet()
        with self.assertRaises(UserError):
            sheet._create_employee_reimbursement_invoice()

    def test_approve_own_account_creates_invoices(self):
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        employee_partner = sheet.employee_id.sudo().work_contact_id
        supplier_invoices = sheet.account_move_ids.filtered(
            lambda move: move.partner_id == self.vendor
        )
        employee_invoices = sheet.account_move_ids.filtered(
            lambda move: move.partner_id == employee_partner
        )
        self.assertEqual(len(supplier_invoices), 1)
        self.assertEqual(len(employee_invoices), 1)
        self.assertEqual(supplier_invoices.expense_sheet_id, sheet)

    def test_create_supplier_invoices_without_vendor(self):
        sheet = self.create_expense_report(
            {
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 100.0,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        invoices = sheet._create_supplier_invoices()
        self.assertFalse(invoices)

    def test_action_sheet_move_post_without_moves_raises(self):
        sheet = self._create_own_account_sheet()
        with self.assertRaises(UserError):
            sheet.action_sheet_move_post()

    def test_action_sheet_move_post(self):
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        self.assertEqual(sheet.state, "done")
        posted_moves = sheet.account_move_ids.filtered(
            lambda move: move.state == "posted"
        )
        self.assertTrue(posted_moves)

    def test_action_reset_expense_sheets_clears_moves(self):
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        sheet.action_reset_expense_sheets()
        self.assertFalse(sheet.account_move_ids)
        self.assertFalse(sheet.accounting_date)

    def test_action_open_account_moves(self):
        sheet = self._create_own_account_sheet()
        invoice = sheet._create_supplier_invoices()
        action = sheet.action_open_account_moves()
        self.assertEqual(action["type"], "ir.actions.act_window")
        self.assertEqual(action["res_model"], "account.move")
        self.assertEqual(action["res_id"], invoice.id)
        self.assertEqual(action["view_mode"], "form")

    def test_action_open_account_moves_multiple(self):
        sheet = self._create_own_account_sheet()
        sheet._create_supplier_invoices()
        sheet._create_employee_reimbursement_invoice()
        action = sheet.action_open_account_moves()
        self.assertEqual(len(sheet.account_move_ids), 2)
        self.assertNotIn("res_id", action)

    def test_res_config_settings_reimbursement_accounts(self):
        settings = self.env["res.config.settings"].create(
            {
                "company_id": self.company.id,
                "hr_expense_reimbursement_debit_account_id": self.company_data[
                    "default_account_expense"
                ].id,
                "hr_expense_reimbursement_credit_account_id": self.company_data[
                    "default_account_payable"
                ].id,
            }
        )
        settings.execute()
        self.assertEqual(
            self.company.hr_expense_reimbursement_debit_account_id,
            self.company_data["default_account_expense"],
        )
        self.assertEqual(
            self.company.hr_expense_reimbursement_credit_account_id,
            self.company_data["default_account_payable"],
        )

    def test_approve_company_account_does_not_create_vendor_invoices(self):
        sheet = self.create_expense_report(
            {
                "payment_mode": "company_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 1000.00,
                            "tax_ids": [Command.set(self.tax_purchase_a.ids)],
                            "payment_mode": "company_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        self.assertFalse(
            sheet.account_move_ids.filtered(
                lambda move: move.move_type == "in_invoice"
                and move.partner_id == self.vendor
            )
        )

    def test_action_sheet_move_post_company_account(self):
        sheet = self.create_expense_report(
            {
                "payment_mode": "company_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 1000.00,
                            "tax_ids": [Command.set(self.tax_purchase_a.ids)],
                            "payment_mode": "company_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        self.assertTrue(sheet.account_move_ids)

    def test_action_reset_company_account_sheet(self):
        sheet = self.create_expense_report(
            {
                "payment_mode": "company_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 1000.00,
                            "tax_ids": [Command.set(self.tax_purchase_a.ids)],
                            "payment_mode": "company_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        sheet.action_reset_expense_sheets()
        self.assertFalse(sheet.accounting_date)

    def test_create_employee_reimbursement_without_work_contact(self):
        employee = self.env["hr.employee"].create({"name": "No Contact Employee"})
        employee.work_contact_id = False
        sheet = self.create_expense_report(
            {
                "employee_id": employee.id,
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 100.0,
                            "vendor_id": self.vendor.id,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        with self.assertRaises(UserError):
            sheet._create_employee_reimbursement_invoice()

    def test_reconcile_without_credit_account_raises(self):
        self.company.write({"hr_expense_reimbursement_credit_account_id": False})
        sheet = self._create_own_account_sheet()
        with self.assertRaises(UserError):
            sheet._reconcile_account_lines()

    def test_create_supplier_invoices_multiple_vendors(self):
        vendor2 = self.env["res.partner"].create({"name": "Vendor 2"})
        sheet = self.create_expense_report(
            {
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 100.0,
                            "vendor_id": self.vendor.id,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    ),
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 50.0,
                            "vendor_id": vendor2.id,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    ),
                ],
            }
        )
        invoices = sheet._create_supplier_invoices()
        self.assertEqual(len(invoices), 2)
        self.assertEqual(set(invoices.mapped("partner_id")), {self.vendor, vendor2})

    def test_create_employee_reimbursement_skips_zero_amount(self):
        sheet = self.create_expense_report(
            {
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 0.0,
                            "vendor_id": self.vendor.id,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        invoices = sheet._create_employee_reimbursement_invoice()
        self.assertFalse(invoices)

    def test_account_move_expense_sheet_link(self):
        sheet = self._create_own_account_sheet()
        invoice = sheet._create_supplier_invoices()
        self.assertEqual(invoice.expense_sheet_id, sheet)

    def test_is_vendor_bill_sheet(self):
        sheet = self._create_own_account_sheet()
        self.assertTrue(sheet._is_vendor_bill_sheet())
        sheet_no_vendor = self.create_expense_report(
            {
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 100.0,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        self.assertFalse(sheet_no_vendor._is_vendor_bill_sheet())

    def test_approve_own_account_without_vendor_skips_vendor_flow(self):
        sheet = self.create_expense_report(
            {
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 100.0,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        self.assertFalse(
            sheet.account_move_ids.filtered(
                lambda move: move.move_type == "in_invoice"
                and move.partner_id == self.vendor
            )
        )

    def test_supplier_invoice_line_fallback_name(self):
        sheet = self._create_own_account_sheet()
        sheet.expense_line_ids.write({"name": ""})
        invoice = sheet._create_supplier_invoices()
        self.assertIn(self.vendor.name, invoice.invoice_line_ids[0].name)

    def test_create_reimbursement_without_journal_raises(self):
        sheet = self._create_own_account_sheet()
        sheet.journal_id = False
        with self.assertRaises(UserError):
            sheet._create_employee_reimbursement_invoice()

    def test_missing_debit_account_raises(self):
        self.company.write({"hr_expense_reimbursement_debit_account_id": False})
        sheet = self._create_own_account_sheet()
        with self.assertRaises(UserError):
            sheet._create_employee_reimbursement_invoice()

    def test_generate_supplier_payments(self):
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        supplier_invoice = sheet.account_move_ids.filtered(
            lambda move: move.partner_id == self.vendor
        )
        supplier_invoice.action_post()
        sheet._generate_supplier_payments()
        self.assertTrue(supplier_invoice.payment_state in ("paid", "in_payment"))

    def test_generate_supplier_payments_uses_employee_payments_journal(self):
        employee_journal = self.env["account.journal"].create(
            {
                "name": "Employee payments",
                "type": "bank",
                "code": "EPAY",
                "company_id": self.company.id,
            }
        )
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        supplier_invoice = sheet.account_move_ids.filtered(
            lambda move: move.partner_id == self.vendor
        )
        supplier_invoice.action_post()
        sheet._generate_supplier_payments()
        payments = self.env["account.payment"].search(
            [
                ("journal_id", "=", employee_journal.id),
                ("company_id", "=", self.company.id),
            ]
        )
        self.assertTrue(payments)

    def test_generate_supplier_payments_no_bank_journal_raises(self):
        self.env["account.journal"].search(
            [("type", "=", "bank"), ("company_id", "=", self.company.id)]
        ).write({"active": False})
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        supplier_invoice = sheet.account_move_ids.filtered(
            lambda move: move.partner_id == self.vendor
        )
        supplier_invoice.action_post()
        with self.assertRaises(UserError):
            sheet._generate_supplier_payments()

    def test_reconcile_account_lines_reconciles_matching_lines(self):
        credit_account = self.company.hr_expense_reimbursement_credit_account_id
        offset_account = self.company_data["default_account_expense"]
        sheet = self._create_own_account_sheet()
        move1 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": credit_account.id,
                            "debit": 100.0,
                            "credit": 0.0,
                            "name": "Credit debit",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": offset_account.id,
                            "debit": 0.0,
                            "credit": 100.0,
                            "name": "Offset credit",
                        }
                    ),
                ],
            }
        )
        move2 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": credit_account.id,
                            "debit": 0.0,
                            "credit": 100.0,
                            "name": "Credit credit",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": offset_account.id,
                            "debit": 100.0,
                            "credit": 0.0,
                            "name": "Offset debit",
                        }
                    ),
                ],
            }
        )
        move1.action_post()
        move2.action_post()
        sheet.write(
            {"account_move_ids": [Command.link(move1.id), Command.link(move2.id)]}
        )
        sheet._reconcile_account_lines()
        credit_lines = (move1 | move2).line_ids.filtered(
            lambda line: line.account_id == credit_account
        )
        self.assertEqual(len(credit_lines), 2)
        self.assertTrue(all(line.reconciled for line in credit_lines))

    def test_account_move_payment_state_only_overrides_reimbursement(self):
        reimbursement = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.expense_employee.work_contact_id.id,
                "is_employee_reimbursement": True,
            }
        )
        vendor_bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.vendor.id,
                "is_employee_reimbursement": False,
            }
        )
        (reimbursement | vendor_bill)._compute_payment_state()
        self.assertEqual(reimbursement.payment_state, "not_paid")
        self.assertTrue(vendor_bill.payment_state)

    def test_action_reset_posts_message(self):
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        message_count = len(sheet.message_ids)
        sheet.action_reset_expense_sheets()
        self.assertGreater(len(sheet.message_ids), message_count)
        reset_messages = sheet.message_ids.filtered(
            lambda message: "reset to draft" in (message.body or "").lower()
        )
        self.assertTrue(reset_messages)

    def test_supplier_invoice_with_taxes(self):
        sheet = self.create_expense_report(
            {
                "payment_mode": "own_account",
                "expense_line_ids": [
                    Command.create(
                        {
                            "employee_id": self.expense_employee.id,
                            "product_id": self.product_c.id,
                            "total_amount_currency": 115.0,
                            "tax_ids": [Command.set(self.tax_purchase_a.ids)],
                            "vendor_id": self.vendor.id,
                            "payment_mode": "own_account",
                            "date": self.frozen_today,
                            "company_id": self.company.id,
                            "currency_id": self.company_data["currency"].id,
                        }
                    )
                ],
            }
        )
        invoice = sheet._create_supplier_invoices()
        self.assertEqual(len(invoice.invoice_line_ids), 1)
        self.assertTrue(invoice.invoice_line_ids.tax_ids)

    def test_coverage_boosters(self):
        sheet = self._create_own_account_sheet()
        sheet.action_submit_sheet()
        posted_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": sheet.journal_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 10.0,
                            "credit": 0.0,
                            "name": "Posted move",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                            "debit": 0.0,
                            "credit": 10.0,
                            "name": "Offset",
                        }
                    ),
                ],
            }
        )
        posted_move.action_post()
        cancelled_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": sheet.journal_id.id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 5.0,
                            "credit": 0.0,
                            "name": "Cancelled move",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                            "debit": 0.0,
                            "credit": 5.0,
                            "name": "Offset",
                        }
                    ),
                ],
            }
        )
        cancelled_move.action_post()
        cancelled_move.button_cancel()
        sheet.write(
            {
                "account_move_ids": [
                    Command.link(posted_move.id),
                    Command.link(cancelled_move.id),
                ]
            }
        )
        sheet.action_approve_expense_sheets()
        self.assertFalse(posted_move.exists())
        self.assertFalse(cancelled_move.exists())

        pay_journal = self.env["account.journal"].create(
            {
                "name": "Bank without methods",
                "type": "bank",
                "code": "BNM",
                "company_id": self.company.id,
            }
        )
        pay_journal.outbound_payment_method_line_ids.unlink()
        self.env["account.journal"].search(
            [
                ("type", "=", "bank"),
                ("company_id", "=", self.company.id),
                ("id", "!=", pay_journal.id),
            ]
        ).write({"active": False})
        payment_sheet = self._create_own_account_sheet()
        payment_sheet.action_submit_sheet()
        payment_sheet.action_approve_expense_sheets()
        supplier_invoice = payment_sheet.account_move_ids.filtered(
            lambda move: move.partner_id == self.vendor
        )
        supplier_invoice.action_post()
        payment_sheet._generate_supplier_payments()
        self.assertTrue(pay_journal.outbound_payment_method_line_ids)

        single_line_sheet = self._create_own_account_sheet()
        credit_account = self.company.hr_expense_reimbursement_credit_account_id
        single_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": credit_account.id,
                            "debit": 50.0,
                            "credit": 0.0,
                            "name": "Single credit line",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 0.0,
                            "credit": 50.0,
                            "name": "Offset",
                        }
                    ),
                ],
            }
        )
        single_move.action_post()
        single_line_sheet.write({"account_move_ids": [Command.link(single_move.id)]})
        single_line_sheet._reconcile_account_lines()
        credit_line = single_move.line_ids.filtered(
            lambda line: line.account_id == credit_account
        )
        self.assertFalse(credit_line.reconciled)
