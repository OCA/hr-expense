# Copyright 2026 Camptocamp SA (https://www.camptocamp.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class TimesheetsAnalysisReport(models.Model):
    _inherit = "timesheets.analysis.report"

    manual_reinvoice = fields.Boolean(readonly=True)
    manual_reinvoice_done = fields.Boolean(readonly=True)
    manual_reinvoice_discarded = fields.Boolean(readonly=True)

    @api.model
    def _select(self):
        return (
            super()._select()
            + """,
            A.manual_reinvoice AS manual_reinvoice,
            A.manual_reinvoice_done AS manual_reinvoice_done,
            A.manual_reinvoice_discarded AS manual_reinvoice_discarded
        """
        )
