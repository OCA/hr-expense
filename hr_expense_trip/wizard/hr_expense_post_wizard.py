# Copyright 2026 Odoo Community Association (OCA)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models


class HrExpensePostWizard(models.TransientModel):
    _inherit = "hr.expense.post.wizard"

    def action_post_entry(self):
        action = super().action_post_entry()

        trip_id = self.env.context.get("trip_attachment_source_id")
        if not trip_id:
            return action

        trip = self.env["hr.trip"].browse(trip_id).exists()
        if not trip:
            return action

        expenses = self.env["hr.expense"].browse(self.env.context.get("active_ids", []))
        moves = expenses.mapped("account_move_id")
        if not moves:
            return action

        trip._ensure_trip_report_created()
        source_attachments = trip._gather_trip_attachments()
        trip._copy_attachments_to_moves(moves, source_attachments)
        return action
