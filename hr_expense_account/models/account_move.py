# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import base64
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        moves = super()._post(soft=soft)
        for move in moves:
            if move.expense_ids:
                move.payment_reference = move.payment_reference or move.name
                move._ensure_invoice_pdf_with_expense_attachments(replace_existing=True)

        return moves

    def _ensure_invoice_pdf_with_expense_attachments(self, replace_existing=False):
        self.ensure_one()
        if self.move_type != "in_invoice" or not self.expense_ids:
            return

        try:
            if replace_existing and self.invoice_pdf_report_id:
                self.write({"invoice_pdf_report_file": False})
                self.invalidate_recordset(
                    fnames=["invoice_pdf_report_id", "invoice_pdf_report_file"]
                )

            if self.invoice_pdf_report_id:
                return

            pdf_report = self.env["account.move.send"]._get_default_pdf_report_id(self)
            pdf_content, report_type = (
                self.env["ir.actions.report"]
                .with_context(force_report_rendering=True)
                ._render_qweb_pdf(
                    pdf_report.report_name,
                    [self.id],
                )
            )
            if not pdf_content or report_type not in {"pdf", "application/pdf"}:
                return

            self.write({"invoice_pdf_report_file": base64.b64encode(pdf_content)})
            self.invalidate_recordset(
                fnames=["invoice_pdf_report_id", "invoice_pdf_report_file"]
            )
            if self.invoice_pdf_report_id:
                self.invoice_pdf_report_id.name = self._get_invoice_report_filename(
                    report=pdf_report
                )
                self.message_main_attachment_id = self.invoice_pdf_report_id
        except Exception:
            _logger.exception(
                "Failed to generate invoice PDF with merged expense "
                "attachments for move %s",
                self.name,
            )
