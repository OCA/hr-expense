# Copyright 2024 Odoo Community Association (OCA)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class HrExpense(models.Model):
    _inherit = "hr.expense"

    trip_id = fields.Many2one(
        comodel_name="hr.trip",
        string="Trip",
        ondelete="set null",
        index=True,
    )
    # Related fields used by decoration-success / decoration-warning in the trip
    # form's expense list to flag dates outside the trip date range.
    trip_start_date = fields.Date(
        related="trip_id.start_date",
        store=False,
    )
    trip_end_date = fields.Date(
        related="trip_id.end_date",
        store=False,
    )

    def action_add_existing_expenses(self):
        self.ensure_one()
        trip_id = self.env.context.get("default_trip_id")
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Add: Expenses"),
            "res_model": "hr.trip",
            "res_id": trip_id,
            "view_mode": "form",
            "target": "new",
        }

    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if "trip_id" in fields_list and not defaults.get("trip_id"):
            expense_date = defaults.get("date")
            employee_id = defaults.get("employee_id")
            if expense_date and employee_id:
                trip = self.env["hr.trip"].search(
                    [
                        ("employee_id", "=", employee_id),
                        ("start_date", "<=", expense_date),
                        ("end_date", ">=", expense_date),
                    ],
                    limit=1,
                )
                if trip:
                    defaults["trip_id"] = trip.id
        return defaults
