# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import io
from unittest.mock import patch

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import file_open, pdf

from odoo.addons.hr_expense.tests.common import TestExpenseCommon

_FAKE_PDF = b"%PDF-1.4 fake"
_MOCK_RENDER_PDF = (
    "odoo.addons.base.models.ir_actions_report.IrActionsReport._render_qweb_pdf"
)
_MOCK_PREPARE_STREAMS = (
    "odoo.addons.account.models.ir_actions_report.IrActionsReport."
    "_render_qweb_pdf_prepare_streams"
)


@tagged("post_install", "-at_install")
class TestHrExpenseAccount(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Set a purchase journal on the company so journal resolution is deterministic
        cls.purchase_journal = cls.env["account.journal"].search(
            [
                *cls.env["account.journal"]._check_company_domain(cls.env.company),
                ("type", "=", "purchase"),
            ],
            limit=1,
        )
        cls.env.company.expense_journal_id = cls.purchase_journal

    def _make_expense(self, payment_mode="own_account"):
        return self.create_expenses(
            [{"payment_mode": payment_mode, "name": "Test Expense"}]
        )

    def _submit(self, expense):
        expense.with_user(self.expense_user_employee).action_submit()

    def _approve(self, expense):
        expense.with_user(self.expense_user_manager).action_approve()

    def _make_draft_vendor_bill(self):
        account_domain = self.env["account.account"]._check_company_domain(
            self.env.company
        )
        expense_account = self.env["account.account"].search(
            [*account_domain, ("account_type", "=", "expense")], limit=1
        )
        vendor = self.env["res.partner"].create({"name": "Split Vendor"})
        return self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": vendor.id,
                "invoice_date": fields.Date.context_today(self.env.user),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Base Line",
                            "account_id": expense_account.id,
                            "quantity": 1,
                            "price_unit": 11.0,
                        }
                    )
                ],
            }
        )

    # ------------------------------------------------------------------
    # own_account path
    # ------------------------------------------------------------------

    @patch(_MOCK_RENDER_PDF, return_value=(_FAKE_PDF, "application/pdf"))
    def test_post_pdf_copied_to_draft_bill_own_account(self, _mock):
        """The draft vendor bill gets a temporary merged invoice PDF attachment."""
        expense = self._make_expense("own_account")
        self._submit(expense)
        self._approve(expense)
        expense.action_post()

        move = expense.account_move_id
        self.assertTrue(move.invoice_pdf_report_id)
        self.assertEqual(move.invoice_pdf_report_id.mimetype, "application/pdf")

    def test_vendor_bill_invoice_pdf_stream_includes_expense_attachments(self):
        """Vendor bill invoice PDFs include the linked expense attachment pages."""
        minimal_pdf = file_open("base/tests/minimal.pdf", "rb").read()

        with patch(_MOCK_RENDER_PDF, return_value=(minimal_pdf, "application/pdf")):
            expense = self._make_expense("own_account")
            self._submit(expense)
            self._approve(expense)
            expense.action_post()

        move = expense.account_move_id
        fake_streams = {
            move.id: {"stream": io.BytesIO(minimal_pdf), "attachment": False}
        }

        with patch(_MOCK_PREPARE_STREAMS, return_value=fake_streams):
            streams = self.env["ir.actions.report"]._render_qweb_pdf_prepare_streams(
                "account.account_invoices",
                {},
                res_ids=[move.id],
            )

        merged_stream = streams[move.id]["stream"]
        merged_pdf = pdf.OdooPdfFileReader(io.BytesIO(merged_stream.getvalue()))
        self.assertEqual(merged_pdf.getNumPages(), 1)
        merged_stream.close()

    def test_confirm_vendor_bill_creates_invoice_pdf_with_expense_attachments(self):
        """Posting the draft vendor bill stores the merged invoice PDF on the move."""
        minimal_pdf = file_open("base/tests/minimal.pdf", "rb").read()

        with patch(_MOCK_RENDER_PDF, return_value=(minimal_pdf, "application/pdf")):
            expense = self._make_expense("own_account")
            self._submit(expense)
            self._approve(expense)
            expense.action_post()

        move = expense.account_move_id
        fake_streams = {
            move.id: {"stream": io.BytesIO(minimal_pdf), "attachment": False}
        }

        with patch(_MOCK_PREPARE_STREAMS, return_value=fake_streams):
            move.action_post()

        self.assertTrue(move.invoice_pdf_report_id)
        merged_pdf = pdf.OdooPdfFileReader(io.BytesIO(move.invoice_pdf_report_id.raw))
        self.assertEqual(merged_pdf.getNumPages(), 1)

    def test_confirm_vendor_bill_replaces_existing_invoice_pdf(self):
        """Posting removes the draft PDF and regenerates a fresh merged invoice PDF."""
        expense_pdf = b"%PDF-1.4 expense"
        # draft_pdf = b"%PDF-1.4 draft"
        posted_pdf = b"%PDF-1.4 posted"

        with patch(
            _MOCK_RENDER_PDF,
            side_effect=[
                (expense_pdf, "application/pdf"),
                #      (draft_pdf, "application/pdf"),
                (posted_pdf, "application/pdf"),
            ],
        ):
            expense = self._make_expense("own_account")
            self._submit(expense)
            self._approve(expense)
            expense.action_post()

            move = expense.account_move_id
            draft_attachment = move.invoice_pdf_report_id
            self.assertTrue(draft_attachment)

            move.action_post()
            move.invalidate_recordset(
                ["invoice_pdf_report_id", "invoice_pdf_report_file"]
            )

        self.assertTrue(move.invoice_pdf_report_id)
        self.assertNotEqual(move.invoice_pdf_report_id.id, draft_attachment.id)
        self.assertFalse(draft_attachment.exists())
        self.assertEqual(move.invoice_pdf_report_id.raw, posted_pdf)

    # ------------------------------------------------------------------
    # action_post creates draft (not posted)
    # ------------------------------------------------------------------

    @patch(_MOCK_RENDER_PDF, return_value=(_FAKE_PDF, "application/pdf"))
    def test_action_post_creates_draft_not_posted(self, _mock):
        # Calling action_post() directly on an approved expense creates a draft
        # move without posting.
        expense = self._make_expense("own_account")
        self._submit(expense)
        # Set approval_state to bypass _do_approve (which now calls action_post)
        expense.write({"approval_state": "approved"})

        expense.action_post()

        self.assertTrue(expense.account_move_id)
        self.assertEqual(expense.account_move_id.state, "draft")

    # ------------------------------------------------------------------
    # Reset to draft removes the draft move
    # ------------------------------------------------------------------

    @patch(_MOCK_RENDER_PDF, return_value=(_FAKE_PDF, "application/pdf"))
    def test_reset_removes_draft_move(self, _mock):
        # Resetting an expense to draft deletes the automatically created draft move.
        expense = self._make_expense("own_account")
        self._submit(expense)
        self._approve(expense)
        expense.action_post()

        self.assertTrue(expense.account_move_id)
        expense.action_reset()

        self.assertFalse(
            expense.account_move_id, "Draft move should be removed after reset"
        )
        self.assertEqual(expense.state, "draft")

    # ------------------------------------------------------------------
    # Vendor bill invoice-line split action
    # ------------------------------------------------------------------

    def test_vendor_bill_split_line_duplicate_inserted_below(self):
        # Splitting a draft bill line duplicates it and keeps it directly
        # below the source.
        move = self._make_draft_vendor_bill()

        move.write(
            {
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "Another Line",
                            "account_id": move.invoice_line_ids[0].account_id.id,
                            "quantity": 1,
                            "price_unit": 7.0,
                        }
                    )
                ]
            }
        )

        ordered_before = move.invoice_line_ids.sorted(
            key=lambda line: (line.sequence, line.id)
        )
        source_line = ordered_before[0]
        source_vals = {
            "name": source_line.name,
            "product_id": source_line.product_id.id,
            "account_id": source_line.account_id.id,
            "quantity": source_line.quantity,
            "price_unit": source_line.price_unit,
            "discount": source_line.discount,
            "tax_ids": set(source_line.tax_ids.ids),
        }

        source_line.action_split_duplicate_line()

        ordered_after = move.invoice_line_ids.sorted(
            key=lambda line: (line.sequence, line.id)
        )
        self.assertEqual(len(ordered_after), len(ordered_before) + 1)

        duplicated_line = ordered_after[1]
        self.assertEqual(duplicated_line.sequence, source_line.sequence + 1)
        self.assertEqual(duplicated_line.name, source_vals["name"])
        self.assertEqual(duplicated_line.product_id.id, source_vals["product_id"])
        self.assertEqual(duplicated_line.account_id.id, source_vals["account_id"])
        self.assertEqual(duplicated_line.quantity, source_vals["quantity"])
        self.assertEqual(duplicated_line.price_unit, source_vals["price_unit"])
        self.assertEqual(duplicated_line.discount, source_vals["discount"])
        self.assertEqual(set(duplicated_line.tax_ids.ids), source_vals["tax_ids"])

    def test_vendor_bill_split_line_requires_draft(self):
        """Splitting a posted bill line is blocked."""
        move = self._make_draft_vendor_bill()
        line = move.invoice_line_ids[0]

        move.action_post()
        with self.assertRaises(UserError):
            line.action_split_duplicate_line()
