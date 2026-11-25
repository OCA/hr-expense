# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html


from odoo import models

_EXPENSE_DRAFT_BILL_CTX = "expense_draft_bill"


class HrExpense(models.Model):
    _inherit = "hr.expense"

    def action_post(self):
        """
        Create draft accounting entries for the approved expenses without posting them.

        Sets the ``expense_draft_bill`` context flag so that:
        - ``_post_wizard`` skips the wizard and creates draft moves directly.
        - ``account.payment.action_post`` skips posting the company-paid payment.

        After super() returns, attachments are copied from company-paid expenses to
        their newly created draft moves (for employee-paid expenses this is handled
        automatically by ``_prepare_receipts_vals``).
        """
        return super(
            HrExpense, self.with_context(**{_EXPENSE_DRAFT_BILL_CTX: True})
        ).action_post()

    def _post_wizard(self):
        """
        When ``expense_draft_bill`` is set, create draft moves directly instead of
        opening the posting wizard, and do not call ``action_post`` on the created
        moves.
        """
        if not self.env.context.get(_EXPENSE_DRAFT_BILL_CTX):
            return super()._post_wizard()

        for company, expenses in self.grouped("company_id").items():
            expenses = expenses.with_company(company)
            expense_receipt_vals_list = expenses._prepare_receipts_vals()
            moves = self.env["account.move"].sudo().create(expense_receipt_vals_list)
            for move in moves:
                move._ensure_invoice_pdf_with_expense_attachments()
                move._message_set_main_attachment_id(
                    move.attachment_ids, force=True, filter_xml=False
                )
            # Intentionally do NOT call moves.action_post()

    def _prepare_move_vals(self):
        res = super()._prepare_move_vals()
        max_date = max(self.mapped("date"))
        res["invoice_date"] = max_date
        res["date"] = max_date
        if not res.get("journal_id") and self.company_id.expense_journal_id:
            res["journal_id"] = self.company_id.expense_journal_id.id
        return res

    def _prepare_receipts_vals(self):
        return_vals = super()._prepare_receipts_vals()

        for vals in return_vals:
            vals["move_type"] = "in_invoice"
            vals.pop(
                "attachment_ids", None
            )  # Remove expense_ids to avoid duplication in the move

        return return_vals
