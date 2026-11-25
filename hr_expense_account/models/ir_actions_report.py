# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import io

from odoo import models
from odoo.tools import pdf
from odoo.tools.pdf import (
    DependencyError,
    OdooPdfFileReader,
    OdooPdfFileWriter,
    PdfReadError,
)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _log_attachment_pdf_error(self, move, attachment, error):
        move._message_log(
            body=self.env._(
                "The attachment %(attachment_name)s has not been added to the invoice "
                "PDF due to the following error: '%(error)s'",
                attachment_name=attachment.name,
                error=error,
            )
        )

    def _append_attachment_to_pdf(self, move, attachment, output_pdf, source_streams):
        try:
            attachment_stream = pdf.to_pdf_stream(attachment)
        except Exception as err:
            self._log_attachment_pdf_error(move, attachment, err)
            return False

        if not attachment_stream:
            return False

        source_streams.append(attachment_stream)
        attachment_reader = OdooPdfFileReader(attachment_stream, strict=False)
        try:
            output_pdf.appendPagesFromReader(attachment_reader)
        except (PdfReadError, DependencyError, ValueError, TypeError) as err:
            self._log_attachment_pdf_error(move, attachment, err)
            return False
        return True

    def _get_trip_attachments(self, move):
        # HACK: hr_expense_trip is not in the dependencies of hr_expense_account
        trip_attachments = self.env["ir.attachment"]
        if not (move.expense_ids and "trip_id" in move.expense_ids._fields):
            return trip_attachments

        trips = move.expense_ids.mapped("trip_id")
        if not trips:
            return trip_attachments

        if "attachment_ids" in trips._fields:
            trip_attachments = trips.mapped("attachment_ids")
        else:
            # Fallback for trip models without an explicit attachment_ids field.
            trip_attachments = self.env["ir.attachment"].search(
                [("res_model", "=", trips._name), ("res_id", "in", trips.ids)]
            )

        return self._prepare_local_attachments(trip_attachments)

    def _render_qweb_pdf_prepare_streams(self, report_ref, data, res_ids=None):
        """Append expense attachments to vendor bill invoice PDFs.

        This hook is used by both manual printing and the invoice PDF generation
        flow that stores ``invoice_pdf_report_id`` when a bill is posted.
        """
        streams = super()._render_qweb_pdf_prepare_streams(
            report_ref, data, res_ids=res_ids
        )
        if not res_ids:
            return streams

        report = self._get_report(report_ref)
        if not report._is_invoice_report(report_ref):
            return streams

        moves = (
            self.env["account.move"]
            .browse(res_ids)
            .filtered(lambda move: move.move_type == "in_invoice" and move.expense_ids)
        )
        if not moves:
            return streams

        for move in moves:
            move_stream_data = streams.get(move.id)
            if not move_stream_data or not move_stream_data.get("stream"):
                continue

            source_streams = [move_stream_data["stream"]]
            output_pdf = OdooPdfFileWriter()
            invoice_reader = OdooPdfFileReader(move_stream_data["stream"], strict=False)
            output_pdf.appendPagesFromReader(invoice_reader)

            # Add trip attachments first when expenses are linked to trips.
            for attachment in self._get_trip_attachments(move):
                self._append_attachment_to_pdf(
                    move, attachment, output_pdf, source_streams
                )

            for expense in move.expense_ids:
                attachments = self._prepare_local_attachments(expense.attachment_ids)
                for attachment in attachments:
                    self._append_attachment_to_pdf(
                        move, attachment, output_pdf, source_streams
                    )

            if len(source_streams) == 1:
                continue

            merged_stream = io.BytesIO()
            output_pdf.write(merged_stream)
            move_stream_data["stream"] = merged_stream

            for stream in source_streams:
                stream.close()

        return streams
