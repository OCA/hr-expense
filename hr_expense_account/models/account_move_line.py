# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def action_split_duplicate_line(self):
        """Duplicate an invoice line and insert the copy just below the source line."""
        self.ensure_one()

        move = self.move_id
        if move.state != "draft":
            raise UserError(
                self.env._("You can only duplicate lines on draft vendor bills.")
            )
        if move.move_type != "in_invoice":
            raise UserError(self.env._("You can only duplicate lines on vendor bills."))

        ordered_lines = move.invoice_line_ids.sorted(
            key=lambda line: (line.sequence, line.id)
        )
        if self not in ordered_lines:
            raise UserError(
                self.env._("Only invoice lines can be duplicated from this view.")
            )

        source_index = ordered_lines.ids.index(self.id)

        # Keep visual order stable by reserving self.sequence + 1 for the duplicate.
        # We resequence all following rows from +2 onward to avoid sequence collisions.
        following_lines = ordered_lines[source_index + 1 :]
        for offset, line in enumerate(following_lines, start=2):
            line.sequence = self.sequence + offset

        self.copy(default={"move_id": move.id, "sequence": self.sequence + 1})
        return True
