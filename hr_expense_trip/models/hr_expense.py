# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    trip_id = fields.Many2one(
        comodel_name="hr.trip",
        ondelete="set null",
        index=True,
        domain="[('employee_id', '=', employee_id)]",
    )
    # Related fields used by decoration-success / decoration-warning in the trip
    # form's expense list to flag dates outside the trip date range.
    trip_start_date = fields.Datetime(related="trip_id.start_date", store=False)
    trip_end_date = fields.Datetime(related="trip_id.end_date", store=False)
    trip_state = fields.Selection(related="trip_id.state", store=False)

    @api.model
    def _check_trips_not_done(self, trips):
        """Raise if an expense is linked to or unlinked from a done trip."""
        done_trips = trips.filtered(lambda trip: trip.state == "done")
        if done_trips:
            raise UserError(
                self.env._(
                    "Trip '%(trip)s' is done and its expenses can no longer be "
                    "changed. Use 'Add More Receipts' on the trip to reopen it.",
                    trip=done_trips[0].code,
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        trip_ids = {vals["trip_id"] for vals in vals_list if vals.get("trip_id")}
        if trip_ids:
            self._check_trips_not_done(self.env["hr.trip"].browse(trip_ids))
        return super().create(vals_list)

    def write(self, vals):
        if "trip_id" in vals:
            new_trip = self.env["hr.trip"].browse(vals["trip_id"] or [])
            changed = self.filtered(lambda expense: expense.trip_id != new_trip)
            if changed:
                self._check_trips_not_done(changed.trip_id | new_trip)
        return super().write(vals)

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

    def action_post(self):
        # Check if any expense has a linked trip that is not in "done" state
        for expense in self:
            if expense.trip_id and expense.trip_id.state != "done":
                raise UserError(
                    self.env._(
                        "Cannot post expense '%(expense)s' because it is linked to "
                        "trip '%(trip)s' which is not in 'Done' state. "
                        "Please mark the trip as done first.",
                        expense=expense.name,
                        trip=expense.trip_id.code,
                    )
                )
        return super().action_post()

    def _prepare_trip_create_vals(self, employee, expenses):
        """Prepare values for creating a trip from selected expenses.

        This hook exists so downstream modules can override trip defaults.
        """
        expense_dates = expenses.mapped("date")
        return {
            "employee_id": employee.id,
            "start_date": min(expense_dates),
            "end_date": max(expense_dates),
        }

    def _prepare_receipts_vals(self):
        return_vals = []
        for (trip_id), expenses_sudo in (
            self.sudo().grouped(lambda x: (x.trip_id)).items()
        ):
            for val in super(HrExpense, expenses_sudo)._prepare_receipts_vals():
                if not trip_id:
                    return_vals.append(val)
                    continue
                ref = val.pop("ref", None)
                start = (
                    trip_id.start_date.strftime("%d.%m.%Y")
                    if trip_id.start_date
                    else ""
                )
                end = trip_id.end_date.strftime("%d.%m.%Y") if trip_id.end_date else ""
                ref = f"{trip_id.code} ({start} - {end})"
                if trip_id.name:
                    ref = f"{ref}: {trip_id.name}"
                return_vals.append(
                    {
                        **val,
                        "ref": ref,
                    }
                )
        return return_vals

    def action_create_trip(self):
        if not self:
            return False

        already_linked = self.filtered("trip_id")
        if already_linked:
            raise UserError(
                self.env._(
                    "Some selected expenses are already linked to a trip. "
                    "Please unselect them before creating trips."
                )
            )

        expenses_by_employee = defaultdict(lambda: self.env["hr.expense"])
        for expense in self:
            expenses_by_employee[expense.employee_id] |= expense

        for employee, expenses in expenses_by_employee.items():
            trip_vals = self._prepare_trip_create_vals(employee, expenses)
            trip = self.env["hr.trip"].create(trip_vals)
            expenses.write({"trip_id": trip.id})
            # Same approval flow as a trip created from the trip form
            trip.action_request_approval()
        return False
