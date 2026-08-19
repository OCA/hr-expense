# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64
import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

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
        default=lambda self: self.env.user.employee_id,
    )
    expense_ids = fields.One2many(
        comodel_name="hr.expense",
        inverse_name="trip_id",
        domain="[('employee_id', '=', employee_id), ('trip_id', 'in', [False, id])]",
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
    )
    can_edit_trip_info = fields.Boolean(compute="_compute_can_edit_trip_info")
    can_create_bill = fields.Boolean(compute="_compute_can_create_bill")

    account_move_ids = fields.Many2many(
        comodel_name="account.move",
        string="Journal Entries",
        compute="_compute_can_create_bill",
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
                sequence_date = fields.Datetime.to_datetime(vals.get("start_date"))
                vals["code"] = self.env["ir.sequence"].with_context(
                    ir_sequence_date=sequence_date
                ).next_by_code("hr.trip") or self.env._("New")
        return super().create(vals_list)

    @api.depends("employee_id")
    def _compute_can_edit_trip_info(self):
        user = self.env.user
        for trip in self:
            trip.can_edit_trip_info = trip._is_user_trip_approver(user)

    @api.depends("expense_ids", "expense_ids.state")
    def _compute_can_create_bill(self):
        for trip in self:
            if not trip.expense_ids:
                trip.can_create_bill = False
                trip.account_move_ids = self.env["account.move"]
            else:
                trip.can_create_bill = trip.state == "done" and all(
                    exp.state == "approved" for exp in trip.expense_ids
                )
                trip.account_move_ids = trip.expense_ids.mapped("account_move_id")

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

    def action_request_approval(self):
        self.ensure_one()
        auto_approve = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("hr_expense_trip.auto_approve", default="True")
        )
        if auto_approve == "True" or self._is_user_trip_approver():
            self.state = "receipts"
        else:
            self.state = "request"
            manager_employee = self.employee_id.parent_id
            manager = manager_employee.user_id if manager_employee else False
            if manager:
                activity_type = self.env.ref("mail.mail_activity_data_todo")
                self.activity_schedule(
                    activity_type_id=activity_type.id,
                    summary=self.env._("Trip Approval Request"),
                    user_id=manager.id,
                )

    def action_approve(self):
        self.ensure_one()
        if not self._is_user_trip_approver():
            raise AccessError(self.env._("You are not allowed to approve this trip."))
        self.state = "receipts"

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

    def write(self, vals):
        if self.env.context.get("skip_trip_write_protection"):
            return super().write(vals)

        state_only_done_transition = (
            set(vals) == {"state"} and vals.get("state") == "done"
        )
        state_only_receipts_transition = (
            set(vals) == {"state"} and vals.get("state") == "receipts"
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

        if "expense_ids" in vals and any(trip.state == "done" for trip in self):
            # Only managers and administrators can edit expenses in "done" state
            if not any(trip._is_user_trip_approver() for trip in self):
                raise AccessError(
                    self.env._(
                        "Expenses cannot be modified once the trip is marked as done."
                    )
                )

        protected_fields = set(vals) - {"expense_ids"}
        if protected_fields and not (
            state_only_done_transition or state_only_receipts_transition
        ):
            blocked_trips = self.filtered(
                lambda trip: trip.state in ("receipts", "done")
                and not trip._is_user_trip_approver()
            )
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
        self.state = "done"
        self._ensure_trip_report_created()

    def action_add_more_receipts(self):
        self.ensure_one()
        self.state = "receipts"

    def _ensure_trip_report_created(self):
        """Ensure trip report PDF exists on trip message thread.

        Uses existing attachment if already created, otherwise generates and creates
        new one.
        Idempotent: safe to call multiple times.
        """
        self.ensure_one()
        # Check if trip report already exists in message attachments
        existing_report = self.env["ir.attachment"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("name", "ilike", "Trip Report.pdf"),
                ("mimetype", "=", "application/pdf"),
            ],
            limit=1,
        )
        if existing_report:
            return existing_report

        # Generate trip report PDF
        pdf_content, _mime = self.env["ir.actions.report"]._render_qweb_pdf(
            "hr_expense_trip.action_report_hr_trip", res_ids=self.ids
        )
        attachment = self.env["ir.attachment"].create(
            {
                "name": self.env._("%s - Trip Report.pdf", self.name),
                "type": "binary",
                "datas": base64.b64encode(pdf_content),
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/pdf",
            }
        )
        # Post to message thread
        self.with_context(skip_trip_write_protection=True).message_post(
            attachment_ids=[attachment.id]
        )
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
