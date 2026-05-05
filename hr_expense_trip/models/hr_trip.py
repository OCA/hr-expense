# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64
import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

_logger = logging.getLogger(__name__)


class HrTrip(models.Model):
    _name = "hr.trip"
    _description = "HR Trip"
    _order = "start_date desc, name"
    _inherit = ["mail.thread.main.attachment", "mail.activity.mixin"]

    code = fields.Char(
        required=True,
        default=lambda self: self.env._("New"),
        copy=False,
    )
    name = fields.Text()
    start_date = fields.Datetime(required=True)
    end_date = fields.Datetime(required=True)
    partner_id = fields.Many2one(comodel_name="res.partner")
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        domain=[("filter_for_expense", "=", True)],
        default=lambda self: self.env.user.employee_id,
    )
    expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="trip_id",
        domain="[('employee_id', '=', employee_id), "
        "('trip_id', 'in', [False, id]), "
        "('state', 'in', ['draft', 'submitted', 'approved'])]",
    )
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ("request", "Requested"),
            ("receipts", "Collect Receipts"),
            ("done", "Done"),
        ],
        default="draft",
        tracking=True,
        copy=False,
    )
    can_edit_trip_info = fields.Boolean(
        compute="_compute_can_edit_trip_info",
        help="Whether the current user may edit the trip information "
        "(name, dates, employee, partner) in the current state.",
    )
    can_create_bill = fields.Boolean(compute="_compute_can_create_bill")

    account_move_ids = fields.Many2many(
        comodel_name="account.move",
        string="Journal Entries",
        compute="_compute_account_move_ids",
        # Employees have no access to journal entries but must be able to
        # open their trips
        compute_sudo=True,
    )
    report_attachment_id = fields.Many2one(
        comodel_name="ir.attachment",
        string="Trip Report",
        copy=False,
        readonly=True,
    )

    @api.depends("code")
    def _compute_display_name(self):
        res = super()._compute_display_name()
        for trip in self:
            if trip.code:
                trip.display_name = f"{trip.code}: {trip.display_name}"
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("code") or vals["code"] == self.env._("New"):
                # Quick-create (name_create) only passes the name; the context
                # defaults are merged by super().create(), so read them here.
                sequence_vals = self._get_sequence_vals(vals)
                sequence_date = (
                    fields.Datetime.to_datetime(sequence_vals.get("start_date"))
                    or fields.Datetime.now()
                )
                company = self._get_sequence_company(sequence_vals)
                vals["code"] = self.env["ir.sequence"].with_company(
                    company
                ).with_context(ir_sequence_date=sequence_date).next_by_code(
                    "hr.trip"
                ) or self.env._("New")
        return super().create(vals_list)

    @api.model
    def _get_sequence_vals(self, vals):
        """Return the values relevant for the trip code, completed with the
        context defaults that would otherwise only be applied by create()."""
        sequence_vals = dict(vals)
        for field_name in ("start_date", "employee_id"):
            if not sequence_vals.get(field_name):
                default = self.env.context.get(f"default_{field_name}")
                if default:
                    sequence_vals[field_name] = default
        return sequence_vals

    @api.model
    def _get_sequence_company(self, vals):
        """Return the company whose trip sequence is used for the new trip.

        The trip belongs to its employee's company; the current company is only
        used when the employee has none.
        """
        employee = self.env["hr.employee"].browse(vals.get("employee_id"))
        return employee.company_id or self.env.company

    @api.depends("state", "employee_id")
    @api.depends_context("uid")
    def _compute_can_edit_trip_info(self):
        """Trip information is open until approval, then reserved to approvers,
        and frozen once the trip is done."""
        user = self.env.user
        for trip in self:
            if trip.state == "done":
                trip.can_edit_trip_info = False
            elif trip.state == "receipts":
                trip.can_edit_trip_info = trip._is_user_trip_approver(user)
            else:
                trip.can_edit_trip_info = True

    @api.depends("state", "expense_ids", "expense_ids.state")
    def _compute_can_create_bill(self):
        for trip in self:
            trip.can_create_bill = (
                bool(trip.expense_ids)
                and trip.state == "done"
                and all(exp.state == "approved" for exp in trip.expense_ids)
            )

    @api.depends("expense_ids.account_move_id")
    def _compute_account_move_ids(self):
        for trip in self:
            trip.account_move_ids = trip.expense_ids.account_move_id

    @api.constrains("employee_id", "start_date", "end_date")
    def _check_no_overlapping_trips(self):
        for trip in self:
            if not trip.employee_id or not trip.start_date or not trip.end_date:
                continue
            overlapping = self.search(
                [
                    ("id", "!=", trip.id),
                    ("employee_id", "=", trip.employee_id.id),
                    ("start_date", "<", trip.end_date),
                    ("end_date", ">", trip.start_date),
                ],
                limit=1,
            )
            if overlapping:
                raise ValidationError(
                    self.env._(
                        "Trip '%(trip)s' overlaps with existing trip '%(other)s' "
                        "for employee '%(employee)s'. Trips must not overlap.",
                        trip=trip.name,
                        other=overlapping.name,
                        employee=trip.employee_id.name,
                    )
                )

    def _is_user_trip_approver(self, user=None):
        self.ensure_one()
        user = user or self.env.user
        if user.has_group("hr_expense.group_hr_expense_manager"):
            return True
        if not (
            user.has_group("hr_expense.group_hr_expense_team_approver")
            or user.has_group("hr_expense.group_hr_expense_user")
        ):
            return False
        return (
            self.employee_id.expense_manager_id == user
            or self.employee_id.parent_id.user_id == user
        )

    def action_print_trip(self):
        self.ensure_one()
        return self.env.ref("hr_expense_trip.action_report_hr_trip").report_action(self)

    def _set_state(self, state):
        """Change the trip state on behalf of the action buttons.

        Writing ``state`` directly is reserved to approvers (see ``write``), so
        the buttons write it as superuser once the caller passed their checks.
        """
        self.check_access("write")
        self.sudo().write({"state": state})

    def action_request_approval(self):
        self.ensure_one()
        require_approval = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hr_expense_trip.require_approval")
        )
        if not require_approval or self._is_user_trip_approver():
            self._set_state("receipts")
        else:
            self._set_state("request")
            approver = self._get_trip_approver_user()
            if approver:
                self.activity_schedule(
                    "hr_expense_trip.mail_act_trip_approval",
                    summary=self.env._("Trip Approval Request"),
                    user_id=approver.id,
                )

    def _get_trip_approver_user(self):
        """Return the user who is asked to approve the trip.

        The employee's manager, or the expense approver as a fallback.
        """
        self.ensure_one()
        employee = self.employee_id
        return employee.parent_id.user_id or employee.expense_manager_id

    def action_approve(self):
        self.ensure_one()
        if not self._is_user_trip_approver():
            raise AccessError(self.env._("You are not allowed to approve this trip."))
        self._set_state("receipts")
        self.activity_feedback(["hr_expense_trip.mail_act_trip_approval"])

    def action_open_account_move(self):
        self.ensure_one()
        moves = self.expense_ids.mapped("account_move_id")
        action = {
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "name": "Journal Entries",
        }
        if len(moves) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": moves.id,
                    "views": [(False, "form")],
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", moves.ids)],
                }
            )
        return action

    @api.model
    def _get_done_trip_writable_fields(self):
        """Fields that may still be written once the trip is done.

        ``state`` is needed by the buttons to reopen the trip, the attachment
        fields are written while the trip report is posted in the chatter.
        """
        return {"state", "report_attachment_id", "message_main_attachment_id"}

    def _check_done_trips_locked(self, vals):
        """Raise if ``vals`` would modify a trip that is done.

        A done trip is frozen for everyone, including administrators and
        superuser. It can only be reopened with "Add More Receipts".
        """
        locked_fields = set(vals) - self._get_done_trip_writable_fields()
        if not locked_fields:
            return
        done_trips = self.filtered(lambda trip: trip.state == "done")
        if done_trips:
            raise UserError(
                self.env._(
                    "Trip '%(trip)s' is done and can no longer be modified. "
                    "Use 'Add More Receipts' to reopen it.",
                    trip=done_trips[0].code,
                )
            )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        for trip in self:
            if trip.state == "done":
                raise UserError(
                    self.env._(
                        "Trip '%(trip)s' is done and can no longer be deleted.",
                        trip=trip.code,
                    )
                )

    def write(self, vals):
        self._check_done_trips_locked(vals)
        if self.env.su:
            return super().write(vals)

        if "state" in vals and not all(trip._is_user_trip_approver() for trip in self):
            raise AccessError(
                self.env._(
                    "The trip status can only be changed with the buttons on the trip."
                )
            )

        if "employee_id" in vals:
            blocked_trips = self.filtered(
                lambda trip: trip.expense_ids
                and trip.employee_id.id != vals["employee_id"]
            )
            if blocked_trips:
                raise ValidationError(
                    self.env._(
                        "You cannot change the employee once expenses are "
                        "linked to the trip."
                    )
                )

        # Posting the trip report sets the main attachment of the chatter
        protected_fields = set(vals) - {"expense_ids", "message_main_attachment_id"}
        if protected_fields:
            blocked_trips = self.filtered(lambda trip: not trip.can_edit_trip_info)
            if blocked_trips:
                raise AccessError(
                    self.env._(
                        "Only managers and administrators can edit trip information "
                        "after approval."
                    )
                )

        return super().write(vals)

    def action_done(self):
        self.ensure_one()
        draft_expenses = self.expense_ids.filtered(
            lambda expense: expense.state == "draft"
        )
        for expense in draft_expenses:
            submit_user = expense.employee_id.user_id or self.env.user
            expense.with_user(submit_user).action_submit()
        self._set_state("done")
        # Expenses may have changed since the last report, e.g. after
        # "Add More Receipts"
        self._ensure_trip_report_created(refresh=True)

    def action_add_more_receipts(self):
        self.ensure_one()
        self._set_state("receipts")

    def _ensure_trip_report_created(self, refresh=False):
        """Ensure the trip report PDF exists and is posted on the trip.

        The existing report is reused unless ``refresh`` is set, in which case
        it is rendered again with the current trip data.
        """
        self.ensure_one()
        attachment = self.report_attachment_id
        if attachment and not refresh:
            return attachment

        pdf_content, _mime = self.env["ir.actions.report"]._render_qweb_pdf(
            "hr_expense_trip.action_report_hr_trip", res_ids=self.ids
        )
        vals = {
            "name": self.env._("%s - Trip Report.pdf", self.code),
            "datas": base64.b64encode(pdf_content),
        }
        if attachment:
            attachment.write(vals)
        else:
            attachment = self.env["ir.attachment"].create(
                {
                    **vals,
                    "type": "binary",
                    "res_model": self._name,
                    "res_id": self.id,
                    "mimetype": "application/pdf",
                }
            )
            self.sudo().report_attachment_id = attachment
        self.message_post(attachment_ids=attachment.ids)
        return attachment

    def _gather_trip_attachments(self):
        """Gather all attachments related to the trip for propagation to moves.

        Returns union of:
        - Trip's own attachments (from message thread)
        - All attachments from related expenses

        Returns ir.attachment recordset, deduplicated by id.
        """
        self.ensure_one()
        trip_attachments = self.env["ir.attachment"]

        # Collect trip's own attachments
        trip_attachments |= self.env["ir.attachment"].search(
            [("res_model", "=", self._name), ("res_id", "=", self.id)]
        )

        # Collect all attachments from related expenses
        for expense in self.expense_ids:
            trip_attachments |= expense.attachment_ids

        return trip_attachments

    def _copy_attachments_to_moves(self, target_moves, source_attachments):
        """Copy source attachments to all target account.move records.

        Handles binary and URL attachment types. Deduplicates per move using
        checksum-based identity to avoid duplicate copies. Failures on individual
        attachments are logged but do not abort the propagation.

        Args:
            target_moves: recordset of account.move to attach to
            source_attachments: recordset of ir.attachment to copy from
        """
        if not target_moves or not source_attachments:
            return

        # Track copied attachment checksums per move to avoid duplicates
        # Use checksum for binary attachments, (type, name, url) tuple for URLs
        for move in target_moves:
            move_attachment_identities = set()
            # Collect existing attachment identities
            for existing_att in move.attachment_ids:
                if existing_att.type == "binary" and existing_att.checksum:
                    move_attachment_identities.add(("binary", existing_att.checksum))
                elif existing_att.type == "url":
                    move_attachment_identities.add(
                        ("url", existing_att.name, existing_att.url)
                    )

            for source_att in source_attachments:
                try:
                    # Determine attachment identity
                    if source_att.type == "binary" and source_att.checksum:
                        att_identity = ("binary", source_att.checksum)
                    elif source_att.type == "url":
                        att_identity = ("url", source_att.name, source_att.url)
                    else:
                        # Skip attachments without reliable identity
                        continue

                    # Skip if already attached to this move
                    if att_identity in move_attachment_identities:
                        continue

                    # Copy attachment data for this move
                    copy_data = source_att.copy_data(
                        {
                            "res_model": "account.move",
                            "res_id": move.id,
                        }
                    )[0]

                    # Create copy as attachment
                    self.env["ir.attachment"].create(copy_data)
                    move_attachment_identities.add(att_identity)

                except Exception as e:
                    # Log failure but continue with other attachments
                    _logger.warning(
                        f"Failed to copy attachment '{source_att.name}' "
                        f"to account.move {move.id}: {str(e)}"
                    )
                    continue

    def action_post(self):
        """Post approved expenses and attach trip-related attachments to resulting
        moves.

        For company-paid expenses, moves are created immediately and can be attached
        synchronously.
        For employee-paid expenses, attachment is deferred via wizard-side integration.
        """
        self.ensure_one()
        if not self.can_create_bill:
            raise AccessError(
                self.env._("All expenses must be in approved state to create a bill.")
            )

        # Ensure trip PDF is created and attached to trip message thread
        self._ensure_trip_report_created()

        # Filter approved expenses for posting
        expenses = self.expense_ids.filtered(lambda e: e.state == "approved")
        if not expenses:
            return False

        # Post expenses and gather resulting company-paid moves
        posting_result = expenses.with_context(
            trip_attachment_source_id=self.id
        ).action_post()

        # For company-paid expenses, moves exist immediately after posting
        # Collect moves and attach trip + expense attachments
        company_paid_moves = expenses.filtered(
            lambda e: e.payment_mode == "company_account"
        ).mapped("account_move_id")

        if company_paid_moves:
            # Gather all trip and expense attachments
            source_attachments = self._gather_trip_attachments()
            # Propagate to all company-paid moves
            self._copy_attachments_to_moves(company_paid_moves, source_attachments)

        # Return posting result (action dict for wizard, False/None otherwise)
        return posting_result

    def _ensure_trip_report_created_to_moves(self, moves):
        """Deprecated: use _copy_attachments_to_moves instead.

        Kept for backward compatibility. Attaches trip report PDF to moves.
        """
        if not moves:
            return
        # Ensure trip report exists
        trip_report = self._ensure_trip_report_created()
        # Use centralized copy mechanism
        self._copy_attachments_to_moves(moves, trip_report)

    @api.constrains("start_date", "end_date")
    def _check_date_range(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(
                    self.env._(
                        "End date (%(end)s) must not be before start date (%(start)s).",
                        end=rec.end_date,
                        start=rec.start_date,
                    )
                )
