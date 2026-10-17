# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, models


class ResCompany(models.Model):
    _inherit = "res.company"

    def _prepare_trip_sequence_vals(self):
        self.ensure_one()
        return {
            "name": self.env._("HR Trip"),
            "code": "hr.trip",
            "company_id": self.id,
            "prefix": "TP-%(range_year)s-",
            "padding": 4,
            "use_date_range": True,
        }

    def _create_trip_sequence(self):
        vals_list = [company._prepare_trip_sequence_vals() for company in self]
        if vals_list:
            self.env["ir.sequence"].sudo().create(vals_list)

    @api.model
    def setup_company_trip_sequences(self):
        """Create the trip sequence for every company that has none yet."""
        companies_with_sequence = (
            self.env["ir.sequence"]
            .sudo()
            .search([("code", "=", "hr.trip"), ("company_id", "!=", False)])
            .company_id
        )
        companies = self.env["res.company"].search(
            [("id", "not in", companies_with_sequence.ids)]
        )
        companies._create_trip_sequence()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies.sudo()._create_trip_sequence()
        return companies
