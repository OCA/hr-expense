# Copyright 2026 Tecnativa - Víctor Martínez
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for attachment in attachments.filtered(
            lambda x: x.res_model == "hr.expense" and x.res_id
        ):
            expense = self.env["hr.expense"].browse(attachment.res_id)
            if expense.sheet_id:
                attachment.copy(
                    {
                        "res_model": expense.sheet_id._name,
                        "res_id": expense.sheet_id.id,
                    }
                )
        return attachments

    def unlink(self):
        attachments_to_unlink = self.env["ir.attachment"]
        expenses_attachments = self.filtered(lambda x: x.res_model == "hr.expense")
        if expenses_attachments:
            expenses = self.env["hr.expense"].browse(
                expenses_attachments.mapped("res_id")
            )
            for expense in expenses.exists().filtered("sheet_id"):
                checksums = set(expense.attachment_ids.mapped("checksum"))
                attachments_to_unlink += expense.sheet_id.attachment_ids.filtered(
                    lambda att, checksums=checksums: att.checksum in checksums
                )
        sheets_attachments = self.filtered(lambda x: x.res_model == "hr.expense.sheet")
        if sheets_attachments:
            sheets = self.env["hr.expense.sheet"].browse(
                sheets_attachments.mapped("res_id")
            )
            for sheet in sheets.exists():
                checksums = set(
                    (sheet.attachment_ids & sheets_attachments).mapped("checksum")
                )
                attachments_to_unlink += sheet.expense_line_ids.attachment_ids.filtered(
                    lambda att, checksums=checksums: att.checksum in checksums
                )
        self += attachments_to_unlink
        return super().unlink()
