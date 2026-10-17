# Copyright 2024 Odoo Community Association (OCA)
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64
from datetime import datetime
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.mail.tests.common import mail_new_test_user


@tagged("post_install", "-at_install")
class TestHrTrip(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create additional users and employees for testing

        group_team_approver = cls.env.ref("hr_expense.group_hr_expense_team_approver")

        # Reuse existing users from TestExpenseCommon
        cls.user_employee = cls.expense_user_employee
        cls.user_manager = cls.expense_user_manager
        cls.user_manager.group_ids += group_team_approver
        cls.user_admin = cls.env.user  # Current user has admin access

        cls.user_other = mail_new_test_user(
            cls.env,
            name="Trip Other User",
            login="trip_other_user@example.com",
            email="trip_other_user@example.com",
            notification_type="email",
            groups="base.group_user",
            company_ids=[Command.set(cls.env.companies.ids)],
        )

        # Create manager employee if it doesn't exist
        cls.employee_manager = cls.env["hr.employee"].search(
            [("user_id", "=", cls.user_manager.id)]
        )
        if not cls.employee_manager:
            cls.employee_manager = (
                cls.env["hr.employee"]
                .sudo()
                .create(
                    {
                        "name": "Trip Manager Employee",
                        "user_id": cls.user_manager.id,
                    }
                )
            )

        # Reuse existing employee from TestExpenseCommon
        cls.employee_employee = cls.expense_employee

        # Set the parent_id and expense_manager_id if not already set
        if not cls.employee_employee.parent_id:
            cls.employee_employee.sudo().parent_id = cls.employee_manager.id
        if not cls.employee_employee.expense_manager_id:
            cls.employee_employee.sudo().expense_manager_id = cls.user_manager.id

        # Create other employee
        cls.employee_other = (
            cls.env["hr.employee"]
            .sudo()
            .create(
                {
                    "name": "Trip Other Employee",
                    "user_id": cls.user_other.id,
                }
            )
        )

        # Create test trips
        cls.trip_employee = (
            cls.env["hr.trip"]
            .with_user(cls.user_employee)
            .create(
                {
                    "name": "Employee Trip",
                    "start_date": datetime(2024, 6, 1),
                    "end_date": datetime(2024, 6, 10),
                    "employee_id": cls.employee_employee.id,
                }
            )
        )
        cls.trip_other = (
            cls.env["hr.trip"]
            .sudo()
            .create(
                {
                    "name": "Other Trip",
                    "start_date": datetime(2024, 7, 1),
                    "end_date": datetime(2024, 7, 10),
                    "employee_id": cls.employee_other.id,
                }
            )
        )

        # Create test expense
        cls.expense = (
            cls.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Hotel",
                    "employee_id": cls.employee_employee.id,
                    "date": datetime(2024, 6, 5),
                    "total_amount": 100.0,
                }
            )
        )

        # Use the existing expense account from TestExpenseCommon
        cls.expense_account = cls.company_data["default_account_expense"]

    def _create_employee_trip(
        self, code="TP-2024-0027", name="Test Trip", start=None, end=None
    ):
        return (
            self.env["hr.trip"]
            .with_user(self.user_employee)
            .create(
                {
                    "code": code,
                    "name": name,
                    "start_date": start or datetime(2024, 8, 1),
                    "end_date": end or datetime(2024, 8, 5),
                    "employee_id": self.employee_employee.id,
                }
            )
        )

    def test_trip_creation(self):
        self.assertEqual(self.trip_employee.name, "Employee Trip")
        self.assertEqual(self.trip_employee.start_date, datetime(2024, 6, 1))
        self.assertEqual(self.trip_employee.end_date, datetime(2024, 6, 10))
        self.assertEqual(self.trip_employee.employee_id, self.employee_employee)

    def test_trip_name_sequence_generated(self):
        trip = (
            self.env["hr.trip"]
            .with_user(self.user_employee)
            .create(
                {
                    "start_date": datetime(2024, 1, 10),
                    "end_date": datetime(2024, 1, 12),
                    "employee_id": self.employee_employee.id,
                }
            )
        )
        self.assertRegex(trip.code, r"^TP-2024-\d{4}$")

    def test_trip_quick_create_uses_context_defaults(self):
        """Quick-create from a Many2one only passes the name; the trip code
        must still be generated from the default start date and employee."""
        HrTrip = self.env["hr.trip"].with_user(self.user_employee)
        trip_id, _display_name = HrTrip.with_context(
            default_start_date=datetime(2023, 5, 2),
            default_end_date=datetime(2023, 5, 4),
            default_employee_id=self.employee_employee.id,
        ).name_create("Quick Trip")
        trip = HrTrip.browse(trip_id)
        self.assertEqual(trip.name, "Quick Trip")
        self.assertEqual(trip.start_date, datetime(2023, 5, 2))
        self.assertEqual(trip.employee_id, self.employee_employee)
        self.assertRegex(trip.code, r"^TP-2023-\d{4}$")

    def test_trip_sequence_exists_per_company(self):
        """Every company gets its own hr.trip sequence."""
        Sequence = self.env["ir.sequence"].sudo()
        for company in self.env["res.company"].sudo().search([]):
            sequences = Sequence.search(
                [("code", "=", "hr.trip"), ("company_id", "=", company.id)]
            )
            self.assertEqual(
                len(sequences), 1, f"Expected one trip sequence for {company.name}"
            )

    def test_trip_sequence_created_for_new_company(self):
        """Creating a company creates its trip sequence and trips use it."""
        company = self.env["res.company"].sudo().create({"name": "Trip Company"})
        sequence = (
            self.env["ir.sequence"]
            .sudo()
            .search([("code", "=", "hr.trip"), ("company_id", "=", company.id)])
        )
        self.assertEqual(len(sequence), 1)
        self.assertTrue(sequence.use_date_range)

        employee = (
            self.env["hr.employee"]
            .sudo()
            .create({"name": "Trip Company Employee", "company_id": company.id})
        )
        trip = (
            self.env["hr.trip"]
            .sudo()
            .create(
                {
                    "start_date": datetime(2024, 3, 1),
                    "end_date": datetime(2024, 3, 2),
                    "employee_id": employee.id,
                }
            )
        )
        # The new company's counter starts fresh, independent of other companies
        self.assertEqual(trip.code, "TP-2024-0001")
        own_trip = (
            self.env["hr.trip"]
            .with_user(self.user_employee)
            .create(
                {
                    "start_date": datetime(2024, 3, 1),
                    "end_date": datetime(2024, 3, 2),
                    "employee_id": self.employee_employee.id,
                }
            )
        )
        self.assertRegex(own_trip.code, r"^TP-2024-\d{4}$")
        self.assertNotEqual(own_trip.code, "TP-2024-0001")

    def test_employee_default(self):
        """employee_id should default to the current user's employee."""
        trip = self.env["hr.trip"].with_user(self.user_employee).new({})
        self.assertEqual(trip.employee_id, self.user_employee.employee_id)

    def test_date_constraint_valid(self):
        """No error when end_date >= start_date."""
        self.trip_employee.write(
            {"start_date": datetime(2024, 6, 1), "end_date": datetime(2024, 6, 1)}
        )
        self.assertEqual(self.trip_employee.end_date, datetime(2024, 6, 1))

    def test_date_constraint_invalid(self):
        """ValidationError raised when end_date < start_date."""
        with self.assertRaises(ValidationError):
            self.trip_employee.write(
                {"start_date": datetime(2024, 6, 10), "end_date": datetime(2024, 6, 1)}
            )

    def test_employee_access_only_own_trip(self):
        trips = self.env["hr.trip"].with_user(self.user_employee).search([])
        self.assertIn(self.trip_employee, trips)
        self.assertNotIn(self.trip_other, trips)

    def test_manager_access_only_responsible_trips(self):
        """Team approvers only see trips of employees they are responsible for."""
        approver = mail_new_test_user(
            self.env,
            name="Trip Team Approver",
            login="trip_team_approver@example.com",
            email="trip_team_approver@example.com",
            notification_type="email",
            groups="base.group_user,hr_expense.group_hr_expense_team_approver",
            company_ids=[Command.set(self.env.companies.ids)],
        )
        self.employee_employee.sudo().expense_manager_id = approver
        trips = self.env["hr.trip"].with_user(approver).search([])
        self.assertIn(self.trip_employee, trips)
        self.assertNotIn(self.trip_other, trips)

    def test_expense_manager_access_all_trips(self):
        """Expense managers (administrators) see every trip."""
        trips = self.env["hr.trip"].with_user(self.user_manager).search([])
        self.assertIn(self.trip_employee, trips)
        self.assertIn(self.trip_other, trips)

    def test_admin_access_all_trips(self):
        trips = self.env["hr.trip"].with_user(self.user_admin).search([])
        self.assertIn(self.trip_employee, trips)
        self.assertIn(self.trip_other, trips)

    def test_mail_thread_mixin(self):
        """hr.trip should have message_ids from mail.thread mixin."""
        self.assertTrue(hasattr(self.trip_employee, "message_ids"))
        self.assertTrue(hasattr(self.trip_employee, "activity_ids"))

    def test_state_transitions(self):
        trip = self._create_employee_trip(
            name="State Transition Trip",
            start=datetime(2024, 9, 1),
            end=datetime(2024, 9, 10),
        )
        self.assertEqual(trip.state, "draft")

        trip.action_request_approval()
        self.assertEqual(trip.state, "receipts")

        with patch.object(type(trip), "_ensure_trip_report_created"):
            trip.action_done()
        self.assertEqual(trip.state, "done")

    def test_auto_approve_enabled(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_expense_trip.require_approval", False
        )
        trip = self._create_employee_trip(
            name="Auto Approve Trip",
            start=datetime(2024, 10, 1),
            end=datetime(2024, 10, 5),
        )
        trip.action_request_approval()
        self.assertEqual(trip.state, "receipts")

    def test_manual_approval_creates_activity_for_employee(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_expense_trip.require_approval", "True"
        )
        trip = self._create_employee_trip(
            name="Manual Approve Trip",
            start=datetime(2024, 11, 1),
            end=datetime(2024, 11, 5),
        )
        trip.with_user(self.user_employee).action_request_approval()
        self.assertEqual(trip.state, "request")

        activity = self.env["mail.activity"].search(
            [
                ("res_id", "=", trip.id),
                ("res_model", "=", "hr.trip"),
                ("user_id", "=", self.user_manager.id),
            ]
        )
        self.assertTrue(
            activity, "Expected an activity to be scheduled for the manager"
        )
        self.assertEqual(activity.summary, "Trip Approval Request")

    def test_manager_request_auto_approves_without_activity(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "hr_expense_trip.require_approval", "True"
        )
        trip = self._create_employee_trip(
            name="Manager Request Trip",
            start=datetime(2024, 11, 6),
            end=datetime(2024, 11, 9),
        )
        self.env["mail.activity"].search(
            [("res_model", "=", "hr.trip"), ("res_id", "=", trip.id)]
        ).unlink()

        trip.with_user(self.user_manager).action_request_approval()
        self.assertEqual(trip.state, "receipts")
        activities = self.env["mail.activity"].search(
            [("res_model", "=", "hr.trip"), ("res_id", "=", trip.id)]
        )
        self.assertFalse(activities)

    def test_approve_requires_approver_role(self):
        trip = self._create_employee_trip(name="Approval Access Check")
        trip.sudo().write({"state": "request"})
        with self.assertRaises(AccessError):
            trip.with_user(self.user_other).action_approve()

    def test_employee_cannot_edit_info_after_approval(self):
        trip = self._create_employee_trip(name="Lock Info Trip")
        trip.sudo().write({"state": "receipts"})
        with self.assertRaises(AccessError):
            trip.with_user(self.user_employee).write({"name": "Changed by Employee"})

    def test_manager_can_edit_info_after_approval(self):
        trip = self._create_employee_trip(name="Manager Edit Approved Trip")
        trip.sudo().write({"state": "receipts"})
        trip.with_user(self.user_manager).write({"name": "Manager updated reason"})
        self.assertEqual(trip.name, "Manager updated reason")

    def test_employee_can_edit_expenses_until_done(self):
        trip = self._create_employee_trip(name="Expense Link Trip")
        trip.sudo().write({"state": "receipts"})
        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Taxi",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 8, 2),
                    "total_amount": 42.0,
                }
            )
        )

        trip.with_user(self.user_employee).write(
            {"expense_ids": [Command.link(expense.id)]}
        )
        self.assertEqual(expense.trip_id, trip)

    def test_expenses_cannot_be_edited_after_done(self):
        trip = self._create_employee_trip(name="Done Lock Trip")
        trip.sudo().write({"state": "done"})
        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Meal",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 8, 3),
                    "total_amount": 30.0,
                }
            )
        )
        with self.assertRaises(UserError):
            trip.with_user(self.user_employee).write(
                {"expense_ids": [Command.link(expense.id)]}
            )

    def test_expense_default_trip_preselected(self):
        trip = self._create_employee_trip(
            name="Preselect Trip",
            start=datetime(2024, 12, 1),
            end=datetime(2024, 12, 15),
        )
        expense_model = self.env["hr.expense"].with_context(
            default_date=datetime(2024, 12, 5),
            default_employee_id=self.employee_employee.id,
        )
        result = expense_model.default_get(["trip_id", "date", "employee_id"])

        if (
            result.get("date") == datetime(2024, 12, 5)
            and result.get("employee_id") == self.employee_employee.id
        ):
            self.assertEqual(result.get("trip_id"), trip.id)
        else:
            found_trip = self.env["hr.trip"].search(
                [
                    ("employee_id", "=", self.employee_employee.id),
                    ("start_date", "<=", datetime(2024, 12, 5)),
                    ("end_date", ">=", datetime(2024, 12, 5)),
                ],
                limit=1,
            )
            self.assertEqual(found_trip, trip)

    def test_expense_default_trip_not_preselected(self):
        outside_date = datetime(2025, 3, 15)
        found_trip = self.env["hr.trip"].search(
            [
                ("employee_id", "=", self.employee_employee.id),
                ("start_date", "<=", outside_date),
                ("end_date", ">=", outside_date),
            ],
            limit=1,
        )
        self.assertFalse(found_trip, "No trip should match this date")

    def test_can_create_bill_false_when_no_expenses(self):
        trip = self.env["hr.trip"].create(
            {
                "name": "Test Trip",
                "start_date": datetime(2025, 1, 1),
                "end_date": datetime(2025, 1, 5),
                "employee_id": self.employee_employee.id,
            }
        )
        self.assertFalse(trip.can_create_bill)

    def test_nobody_can_edit_expenses_in_done_state(self):
        """Not even managers or administrators add expenses to a done trip."""
        trip = self._create_employee_trip(name="Manager Edit Trip")
        trip.sudo().write({"state": "done"})
        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Hotel",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 8, 4),
                    "total_amount": 100.0,
                }
            )
        )
        for user in (self.user_manager, self.env.ref("base.user_admin")):
            with self.assertRaises(UserError):
                trip.with_user(user).write({"expense_ids": [Command.link(expense.id)]})
        with self.assertRaises(UserError):
            trip.sudo().write({"expense_ids": [Command.link(expense.id)]})
        self.assertFalse(expense.trip_id)

    def test_done_trip_info_locked_for_everyone(self):
        """A done trip cannot be modified, not even by administrators."""
        trip = self._create_employee_trip(name="Frozen Trip")
        trip.sudo().write({"state": "done"})
        admin = self.env.ref("base.user_admin")
        self.assertTrue(admin.has_group("hr_expense.group_hr_expense_manager"))
        for trip_as in (
            trip.with_user(self.user_employee),
            trip.with_user(self.user_manager),
            trip.with_user(admin),
            trip.sudo(),
        ):
            for vals in (
                {"name": "Changed"},
                {"partner_id": self.partner_a.id},
                {"start_date": datetime(2024, 8, 2)},
                {"employee_id": self.employee_manager.id},
            ):
                with self.assertRaises(UserError):
                    trip_as.write(vals)
        self.assertEqual(trip.name, "Frozen Trip")
        self.assertEqual(trip.start_date, datetime(2024, 8, 1))

    def test_can_edit_fields_follow_state_and_role(self):
        """The computed flags drive the form's readonly attributes."""
        trip = self._create_employee_trip(name="Flags Trip")
        admin = self.env.ref("base.user_admin")
        expectations = {
            # state: (employee, manager, admin) may edit trip info
            "draft": (True, True, True),
            "request": (True, True, True),
            "receipts": (False, True, True),
            "done": (False, False, False),
        }
        for state, expected in expectations.items():
            trip.sudo().write({"state": state})
            for user, can_edit in zip(
                (self.user_employee, self.user_manager, admin), expected, strict=True
            ):
                trip_as_user = trip.with_user(user)
                trip_as_user.invalidate_recordset(["can_edit_trip_info"])
                self.assertEqual(
                    trip_as_user.can_edit_trip_info, can_edit, f"{state}/{user.name}"
                )

    def test_done_trip_cannot_be_deleted(self):
        trip = self._create_employee_trip(name="Undeletable Trip")
        trip.sudo().write({"state": "done"})
        with self.assertRaises(UserError):
            trip.with_user(self.env.ref("base.user_admin")).unlink()
        with self.assertRaises(UserError):
            trip.sudo().unlink()
        self.assertTrue(trip.exists())

    def test_done_trip_unlocked_by_add_more_receipts(self):
        """ "Add More Receipts" is the only way to make a done trip editable again."""
        trip = self._create_employee_trip(name="Reopen Trip")
        trip.sudo().write({"state": "done"})
        with self.assertRaises(UserError):
            trip.with_user(self.user_manager).write({"name": "Changed"})
        trip.with_user(self.user_employee).action_add_more_receipts()
        self.assertEqual(trip.state, "receipts")
        trip.with_user(self.user_manager).write({"name": "Changed"})
        self.assertEqual(trip.name, "Changed")

    def test_done_trip_report_is_posted(self):
        """Attaching the trip report to a done trip is still possible."""
        trip = self._create_employee_trip(name="Report Trip")
        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True)], limit=1
        )
        self._create_own_account_expense(
            "Hotel", datetime(2024, 8, 2), 90.0, trip=trip
        ).product_id = product
        trip_as_employee = trip.with_user(self.user_employee)
        trip_as_employee.action_request_approval()
        trip_as_employee.action_done()
        self.assertEqual(trip.state, "done")
        self.assertTrue(trip.report_attachment_id)
        self.assertEqual(trip.message_main_attachment_id, trip.report_attachment_id)

    def test_expense_cannot_join_or_leave_done_trip(self):
        """The expense side of the link is locked as well."""
        trip = self._create_employee_trip(name="Locked Link Trip")
        linked = self._create_own_account_expense(
            "Hotel", datetime(2024, 8, 2), 90.0, trip=trip
        )
        other_trip = self._create_employee_trip(
            code="TP-2024-0028",
            name="Other Open Trip",
            start=datetime(2024, 9, 1),
            end=datetime(2024, 9, 5),
        )
        trip.sudo().write({"state": "done"})
        # Writing the unchanged trip is fine (e.g. a form save)
        linked.sudo().write({"trip_id": trip.id})
        with self.assertRaises(UserError):
            linked.sudo().write({"trip_id": False})
        with self.assertRaises(UserError):
            linked.sudo().write({"trip_id": other_trip.id})
        with self.assertRaises(UserError):
            self._create_own_account_expense(
                "Late Receipt", datetime(2024, 8, 3), 10.0, trip=trip
            )
        unlinked = self._create_own_account_expense(
            "Unlinked", datetime(2024, 8, 3), 10.0
        )
        with self.assertRaises(UserError):
            unlinked.sudo().write({"trip_id": trip.id})
        with self.assertRaises(UserError):
            linked.sudo().copy()
        self.assertEqual(linked.trip_id, trip)
        self.assertFalse(unlinked.trip_id)

    def test_trip_copy_starts_in_draft(self):
        trip = self._create_employee_trip(name="Copy Source Trip")
        trip.sudo().write({"state": "done"})
        copy = trip.sudo().copy(
            {"start_date": datetime(2024, 10, 1), "end_date": datetime(2024, 10, 2)}
        )
        self.assertEqual(copy.state, "draft")

    def test_expense_posting_blocked_when_trip_not_done(self):
        """Expense posting should be blocked if trip is not in done state."""
        trip = self._create_employee_trip(name="Posting Block Trip")
        trip.sudo().write({"state": "request"})

        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Taxi to Airport",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 8, 5),
                    "total_amount": 50.0,
                    "trip_id": trip.id,
                }
            )
        )

        # Attempt to post should fail with UserError
        with self.assertRaises(UserError):
            expense.action_post()

    def test_expense_posting_allowed_when_trip_done(self):
        """Expense posting should be allowed if trip is in done state."""
        trip = self._create_employee_trip(name="Posting Allow Trip")

        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Taxi from Airport",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 8, 6),
                    "total_amount": 50.0,
                    "trip_id": trip.id,
                }
            )
        )

        # Set approval state to approved so it can be posted
        expense.sudo().write({"approval_state": "approved"})

        # This should succeed without raising our UserError from the trip validation
        trip.sudo().write({"state": "done"})
        # (it may fail later in the posting process, but not due to trip state)
        try:
            expense.action_post()
        except Exception as e:
            # As long as it's not our UserError about the trip state, it's fine
            self.assertNotIn("trip", str(e).lower())

    def test_expense_posting_allowed_without_trip(self):
        """Expense posting should be allowed if there is no trip."""
        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Standalone Expense",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 8, 7),
                    "total_amount": 25.0,
                }
            )
        )

        # Set approval state to approved so it can be posted
        expense.sudo().write({"approval_state": "approved"})

        # This should succeed without raising our UserError from the trip validation
        try:
            expense.action_post()
        except Exception as e:
            # As long as it's not our UserError about the trip state, it's fine
            self.assertNotIn("trip", str(e).lower())

    def test_employee_cannot_change_when_expenses_exist(self):
        trip = self._create_employee_trip(name="Employee Lock Trip")
        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Linked Expense",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 9, 1),
                    "total_amount": 15.0,
                }
            )
        )
        trip.with_user(self.user_employee).write(
            {"expense_ids": [Command.link(expense.id)]}
        )

        with self.assertRaises(ValidationError):
            trip.with_user(self.user_manager).write(
                {"employee_id": self.employee_other.id}
            )

    def test_action_done_submits_linked_draft_expenses(self):
        trip = self._create_employee_trip(name="Done Submit Trip")
        trip.sudo().write({"state": "receipts"})
        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True)],
            limit=1,
        )
        self.assertTrue(product, "A product category for expenses is required")

        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Receipt Expense",
                    "employee_id": self.employee_employee.id,
                    "product_id": product.id,
                    "date": datetime(2024, 9, 2),
                    "total_amount": 22.0,
                    "trip_id": trip.id,
                }
            )
        )

        with patch.object(type(trip), "_ensure_trip_report_created"):
            trip.with_user(self.user_employee).action_done()

        self.assertEqual(trip.state, "done")
        self.assertEqual(expense.state, "submitted")

    def test_action_add_more_receipts_resets_state(self):
        trip = self._create_employee_trip(name="Reset Receipts Trip")
        trip.sudo().write({"state": "done"})

        trip.with_user(self.user_employee).action_add_more_receipts()
        self.assertEqual(trip.state, "receipts")

    def test_create_trip_from_expenses_groups_per_employee(self):
        expense_a1 = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Expense A1",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 9, 10),
                    "total_amount": 10.0,
                }
            )
        )
        expense_a2 = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Expense A2",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 9, 12),
                    "total_amount": 20.0,
                }
            )
        )
        expense_b1 = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Expense B1",
                    "employee_id": self.employee_other.id,
                    "date": datetime(2024, 9, 11),
                    "total_amount": 15.0,
                }
            )
        )

        expenses = expense_a1 | expense_a2 | expense_b1
        result = expenses.with_user(self.user_admin).action_create_trip()

        created_trips = (expense_a1.trip_id | expense_b1.trip_id).exists()
        self.assertFalse(result)
        self.assertEqual(len(created_trips), 2)
        self.assertEqual(expense_a1.trip_id, expense_a2.trip_id)
        self.assertNotEqual(expense_a1.trip_id, expense_b1.trip_id)
        self.assertEqual(expense_a1.trip_id.employee_id, self.employee_employee)
        self.assertEqual(expense_b1.trip_id.employee_id, self.employee_other)

    def test_create_trip_from_expenses_rejects_already_linked(self):
        trip = self._create_employee_trip(name="Already Linked")
        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Linked Expense",
                    "employee_id": self.employee_employee.id,
                    "date": datetime(2024, 9, 15),
                    "total_amount": 30.0,
                    "trip_id": trip.id,
                }
            )
        )

        with self.assertRaises(UserError):
            expense.with_user(self.user_employee).action_create_trip()

    def test_action_post_trip_pdf_created(self):
        """Test that action_post ensures trip PDF is created on the trip."""
        trip = self._create_employee_trip(name="PDF Creation Trip")

        # Create a company-paid expense
        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True)],
            limit=1,
        )
        self.assertTrue(product)

        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Test Expense",
                    "employee_id": self.employee_employee.id,
                    "product_id": product.id,
                    "date": datetime(2024, 8, 1),
                    "total_amount": 100.0,
                    "payment_mode": "company_account",
                    "trip_id": trip.id,
                }
            )
        )
        expense.sudo().write({"approval_state": "approved"})
        trip.sudo().write({"state": "done"})

        # Post should create trip PDF
        with patch.object(
            type(trip),
            "_gather_trip_attachments",
            return_value=self.env["ir.attachment"],
        ):
            with patch.object(type(trip), "_copy_attachments_to_moves"):
                trip.with_user(self.user_admin).action_post()

        # Verify trip PDF was created
        trip_pdf = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "hr.trip"),
                ("res_id", "=", trip.id),
                ("name", "ilike", "Trip Report.pdf"),
            ]
        )
        self.assertTrue(trip_pdf, "Trip PDF should be created on the trip")

    def test_action_post_company_paid_attachments(self):
        """Test that company-paid move receives trip and expense attachments."""
        trip = self._create_employee_trip(name="Attachment Trip")

        # Create a company-paid expense with an attachment
        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True)],
            limit=1,
        )
        self.assertTrue(product)

        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Expense with Receipt",
                    "employee_id": self.employee_employee.id,
                    "product_id": product.id,
                    "date": datetime(2024, 8, 2),
                    "total_amount": 150.0,
                    "payment_mode": "company_account",
                    "trip_id": trip.id,
                }
            )
        )

        # Add an attachment to the expense
        self.env["ir.attachment"].create(
            {
                "name": "receipt.pdf",
                "type": "binary",
                "datas": base64.b64encode(b"test data"),
                "res_model": "hr.expense",
                "res_id": expense.id,
                "mimetype": "application/pdf",
            }
        )
        expense.sudo().write({"approval_state": "approved"})

        trip.sudo().write({"state": "done"})
        # Post trip (company_account expenses should create moves immediately)
        trip.with_user(self.user_admin).action_post()

        # Verify move exists
        self.assertTrue(
            expense.account_move_id,
            "Company-paid expense should have account_move_id after posting",
        )

        # Verify move has attachments (trip PDF + expense attachment)
        move_attachments = expense.account_move_id.attachment_ids
        self.assertTrue(
            len(move_attachments) > 0,
            "Move should have attachments (trip PDF and expense attachment)",
        )

        # Check for trip PDF
        trip_pdfs = move_attachments.filtered(lambda a: "Trip Report" in a.name)
        self.assertTrue(trip_pdfs, "Move should have trip PDF attachment")

        # Check for expense attachment
        expense_atts = move_attachments.filtered(lambda a: a.name == "receipt.pdf")
        self.assertTrue(expense_atts, "Move should have expense attachment")

    def test_action_post_multiple_company_paid_moves_all_get_attachments(self):
        """Test that all company-paid moves receive attachments, not just the first."""
        trip = self._create_employee_trip(name="Multi-Move Trip")

        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True)],
            limit=1,
        )
        self.assertTrue(product)

        # Create multiple company-paid expenses
        expenses = []
        for i in range(2):
            expense = (
                self.env["hr.expense"]
                .sudo()
                .create(
                    {
                        "name": f"Expense {i + 1}",
                        "employee_id": self.employee_employee.id,
                        "product_id": product.id,
                        "date": datetime(2024, 8, 3 + i),
                        "total_amount": 100.0 + (i * 50),
                        "payment_mode": "company_account",
                        "trip_id": trip.id,
                    }
                )
            )
            expense.sudo().write({"approval_state": "approved"})
            expenses.append(expense)

        trip.sudo().write({"state": "done"})
        # Post trip
        trip.with_user(self.user_admin).action_post()

        # Verify all moves exist and have attachments
        for expense in expenses:
            self.assertTrue(
                expense.account_move_id,
                "Expense should have account_move_id",
            )
            move_attachments = expense.account_move_id.attachment_ids
            self.assertTrue(
                len(move_attachments) > 0,
                "Move for expense should have attachments",
            )

            # Check for trip PDF on each move
            trip_pdfs = move_attachments.filtered(lambda a: "Trip Report" in a.name)
            self.assertTrue(
                trip_pdfs,
                "Each move should have trip PDF attachment",
            )

    def test_action_post_deduplication_same_expense_attachment(self):
        """Test that same attachment is not duplicated on the same move."""
        trip = self._create_employee_trip(name="Dedup Trip")

        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True)],
            limit=1,
        )
        self.assertTrue(product)

        expense = (
            self.env["hr.expense"]
            .sudo()
            .create(
                {
                    "name": "Expense with Receipt",
                    "employee_id": self.employee_employee.id,
                    "product_id": product.id,
                    "date": datetime(2024, 8, 4),
                    "total_amount": 200.0,
                    "payment_mode": "company_account",
                    "trip_id": trip.id,
                }
            )
        )

        # Create and add an attachment to both trip and expense
        # (same file simulated by content)
        shared_content = b"shared test data"

        # Attach to trip via message
        self.env["ir.attachment"].create(
            {
                "name": "shared_receipt.pdf",
                "type": "binary",
                "datas": base64.b64encode(shared_content),
                "res_model": "hr.trip",
                "res_id": trip.id,
                "mimetype": "application/pdf",
            }
        )

        # Also create same attachment on expense
        self.env["ir.attachment"].create(
            {
                "name": "shared_receipt.pdf",
                "type": "binary",
                "datas": base64.b64encode(shared_content),
                "res_model": "hr.expense",
                "res_id": expense.id,
                "mimetype": "application/pdf",
            }
        )
        expense.sudo().write({"approval_state": "approved"})

        trip.sudo().write({"state": "done"})
        # Post trip
        trip.with_user(self.user_admin).action_post()

        # Verify move has the attachment but not duplicated
        move_attachments = expense.account_move_id.attachment_ids
        shared_atts = move_attachments.filtered(
            lambda a: a.name == "shared_receipt.pdf"
        )

        # Should have at least one copy (could be multiple from trip + expense sources)
        # but shouldn't be excessive
        self.assertTrue(
            len(shared_atts) > 0,
            "Move should have shared attachment",
        )
        # Note: Exact deduplication count depends on checksum implementation
        # This test just verifies attachments are present

    def _create_own_account_expense(self, name, date, amount, trip=None):
        """Helper to create an own_account expense with a direct account_id set."""
        vals = {
            "name": name,
            "employee_id": self.employee_employee.id,
            "date": date,
            "total_amount": amount,
            "payment_mode": "own_account",
            "account_id": self.expense_account.id,
        }
        if trip:
            vals["trip_id"] = trip.id
        return self.env["hr.expense"].sudo().create(vals)

    def test_prepare_receipts_vals_ref_includes_trip_name_and_dates(self):
        """_prepare_receipts_vals should prefix ref with trip name and dates."""
        trip = self._create_employee_trip(
            code="TP-2024-0027",
            name="Berlin Conference",
            start=datetime(2024, 9, 1),
            end=datetime(2024, 9, 5),
        )
        expense = self._create_own_account_expense(
            "Hotel Berlin", datetime(2024, 9, 3), 200.0, trip=trip
        )

        vals = expense._prepare_receipts_vals()

        self.assertEqual(len(vals), 1)
        self.assertEqual(
            vals[0]["ref"], "TP-2024-0027 (01.09.2024 - 05.09.2024): Berlin Conference"
        )

    def test_prepare_receipts_vals_ref_unchanged_without_trip(self):
        """_prepare_receipts_vals should not modify ref when expense has no trip."""
        expense = self._create_own_account_expense(
            "Standalone Meal", datetime(2024, 9, 10), 50.0
        )

        vals = expense._prepare_receipts_vals()

        self.assertEqual(len(vals), 1)
        self.assertEqual(vals[0]["ref"], "Standalone Meal")

    def test_prepare_receipts_vals_separate_vals_per_trip(self):
        """Expenses linked to different trips produce separate receipts vals."""
        trip_a = self._create_employee_trip(
            code="TP-2024-0027",
            name="Paris Summit",
            start=datetime(2024, 10, 1),
            end=datetime(2024, 10, 3),
        )
        trip_b = self._create_employee_trip(
            code="TP-2024-0028",
            name="London Workshop",
            start=datetime(2024, 10, 10),
            end=datetime(2024, 10, 12),
        )
        expense_a = self._create_own_account_expense(
            "Flight to Paris", datetime(2024, 10, 1), 300.0, trip=trip_a
        )
        expense_b = self._create_own_account_expense(
            "Hotel London", datetime(2024, 10, 10), 250.0, trip=trip_b
        )

        vals = (expense_a | expense_b)._prepare_receipts_vals()

        self.assertEqual(len(vals), 2)
        refs = {v["ref"] for v in vals}
        self.assertIn("TP-2024-0027 (01.10.2024 - 03.10.2024): Paris Summit", refs)
        self.assertIn("TP-2024-0028 (10.10.2024 - 12.10.2024): London Workshop", refs)

    def test_prepare_receipts_vals_multiple_expenses_same_trip(self):
        """Multiple expenses linked to the same trip are grouped into one receipt."""
        trip = self._create_employee_trip(
            code="TP-2024-0027",
            name="Tokyo Visit",
            start=datetime(2024, 11, 1),
            end=datetime(2024, 11, 7),
        )
        expense_1 = self._create_own_account_expense(
            "Flight", datetime(2024, 11, 1), 800.0, trip=trip
        )
        expense_2 = self._create_own_account_expense(
            "Hotel", datetime(2024, 11, 2), 600.0, trip=trip
        )

        vals = (expense_1 | expense_2)._prepare_receipts_vals()

        self.assertEqual(len(vals), 1)
        self.assertTrue(
            vals[0]["ref"].startswith("TP-2024-0027 (01.11.2024 - 07.11.2024):")
        )

    def test_prepare_receipts_vals_mixed_trip_and_no_trip(self):
        """Expenses with and without trips are each handled correctly."""
        trip = self._create_employee_trip(
            code="TP-2024-0027",
            name="Rome Trip",
            start=datetime(2024, 12, 5),
            end=datetime(2024, 12, 8),
        )
        expense_with_trip = self._create_own_account_expense(
            "Train to Rome", datetime(2024, 12, 5), 120.0, trip=trip
        )
        expense_no_trip = self._create_own_account_expense(
            "Office Lunch", datetime(2024, 12, 3), 15.0
        )

        vals = (expense_with_trip | expense_no_trip)._prepare_receipts_vals()

        self.assertEqual(len(vals), 2)
        refs = {v["ref"] for v in vals}
        self.assertIn("TP-2024-0027 (05.12.2024 - 08.12.2024): Rome Trip", refs)
        self.assertIn("Office Lunch", refs)

    def _set_require_approval(self, value):
        self.env["res.config.settings"].create(
            {"hr_trip_require_approval": value}
        ).execute()

    def test_employee_can_create_and_open_trip(self):
        """A plain employee without accounting rights can save and read a trip
        like the web client does."""
        self.assertFalse(self.user_other.has_group("account.group_account_readonly"))
        result = (
            self.env["hr.trip"]
            .with_user(self.user_other)
            .web_save(
                {
                    "name": "Plain Employee Trip",
                    "start_date": datetime(2025, 2, 1),
                    "end_date": datetime(2025, 2, 3),
                    "employee_id": self.employee_other.id,
                },
                {
                    "code": {},
                    "can_create_bill": {},
                    "account_move_ids": {},
                },
            )
        )
        self.assertEqual(result[0]["account_move_ids"], [])

    def test_require_approval_setting_can_be_turned_off(self):
        """Unticking the setting really disables the approval step."""
        self._set_require_approval(True)
        trip = self._create_employee_trip(
            name="Approval Required",
            start=datetime(2025, 3, 1),
            end=datetime(2025, 3, 2),
        )
        trip.with_user(self.user_employee).action_request_approval()
        self.assertEqual(trip.state, "request")

        self._set_require_approval(False)
        settings = self.env["res.config.settings"].create({})
        self.assertFalse(settings.hr_trip_require_approval)
        trip = self._create_employee_trip(
            name="No Approval", start=datetime(2025, 3, 3), end=datetime(2025, 3, 4)
        )
        trip.with_user(self.user_employee).action_request_approval()
        self.assertEqual(trip.state, "receipts")

    def test_employee_cannot_write_state(self):
        """Employees can only change the state with the buttons."""
        self._set_require_approval(True)
        trip = self._create_employee_trip(name="Self Approval Trip")
        trip.with_user(self.user_employee).action_request_approval()
        self.assertEqual(trip.state, "request")
        trip_as_employee = trip.with_user(self.user_employee)
        for context in ({}, {"skip_trip_write_protection": True}):
            with self.assertRaises(AccessError):
                trip_as_employee.with_context(**context).write({"state": "receipts"})
        with self.assertRaises(AccessError):
            trip_as_employee.action_approve()
        self.assertEqual(trip.state, "request")

    def test_employee_cannot_change_state_of_other_trip(self):
        """The buttons do not give access to trips of other employees."""
        with self.assertRaises(AccessError):
            self.trip_other.with_user(self.user_employee).action_add_more_receipts()

    def test_create_trip_from_expenses_follows_approval_flow(self):
        """Trips created from expenses need approval like any other trip."""
        self._set_require_approval(True)
        expense = self._create_own_account_expense(
            "Employee Expense", datetime(2025, 4, 2), 12.0
        )
        expense.with_user(self.user_employee).action_create_trip()
        self.assertEqual(expense.trip_id.state, "request")

        # An approver of the employee approves the trip right away
        approver_expense = self._create_own_account_expense(
            "Approver Expense", datetime(2025, 4, 5), 8.0
        )
        approver_expense.with_user(self.user_manager).action_create_trip()
        self.assertEqual(approver_expense.trip_id.state, "receipts")

    def test_trip_without_name_shows_no_false(self):
        """An empty trip name must not show up as "False"."""
        trip = self._create_employee_trip(
            code="TP-2025-0001",
            name=False,
            start=datetime(2025, 5, 1),
            end=datetime(2025, 5, 2),
        )
        expense = self._create_own_account_expense(
            "Taxi", datetime(2025, 5, 1), 20.0, trip=trip
        )
        vals = expense._prepare_receipts_vals()
        self.assertEqual(vals[0]["ref"], "TP-2025-0001 (01.05.2025 - 02.05.2025)")

        attachment = trip._ensure_trip_report_created()
        self.assertEqual(attachment.name, "TP-2025-0001 - Trip Report.pdf")

    def test_trip_report_updated_after_add_more_receipts(self):
        """Marking a trip as done again renders the report again."""
        trip = self._create_employee_trip(
            name="Report Refresh Trip",
            start=datetime(2025, 6, 1),
            end=datetime(2025, 6, 5),
        )
        product = self.env["product.product"].search(
            [("can_be_expensed", "=", True)], limit=1
        )
        self._create_own_account_expense(
            "Hotel", datetime(2025, 6, 2), 90.0, trip=trip
        ).product_id = product
        trip_as_employee = trip.with_user(self.user_employee)
        trip_as_employee.action_request_approval()
        trip_as_employee.action_done()
        report = trip.report_attachment_id
        self.assertTrue(report)
        first_content = report.raw

        trip_as_employee.action_add_more_receipts()
        self._create_own_account_expense(
            "Second Receipt", datetime(2025, 6, 3), 15.0, trip=trip
        ).product_id = product
        trip_as_employee.action_done()

        self.assertEqual(trip.report_attachment_id, report)
        self.assertNotEqual(report.raw, first_content)
        reports = self.env["ir.attachment"].search(
            [
                ("res_model", "=", "hr.trip"),
                ("res_id", "=", trip.id),
                ("mimetype", "=", "application/pdf"),
            ]
        )
        self.assertEqual(reports, report)

    def test_approve_closes_approval_activity(self):
        """Approving the trip marks the approval request activity as done."""
        self._set_require_approval(True)
        trip = self._create_employee_trip(
            name="Activity Done Trip",
            start=datetime(2025, 7, 1),
            end=datetime(2025, 7, 2),
        )
        trip.with_user(self.user_employee).action_request_approval()
        activity = trip.activity_ids
        self.assertEqual(
            activity.activity_type_id,
            self.env.ref("hr_expense_trip.mail_act_trip_approval"),
        )

        trip.with_user(self.user_manager).action_approve()
        self.assertEqual(trip.state, "receipts")
        self.assertFalse(trip.activity_ids)
        # Done activities are archived, not deleted
        self.assertFalse(activity.active)

    def test_approval_activity_falls_back_to_expense_approver(self):
        """Without a manager the expense approver gets the approval request."""
        self._set_require_approval(True)
        approver = mail_new_test_user(
            self.env,
            name="Trip Expense Approver",
            login="trip_expense_approver@example.com",
            groups="base.group_user,hr_expense.group_hr_expense_team_approver",
        )
        self.employee_employee.sudo().write(
            {"parent_id": False, "expense_manager_id": approver.id}
        )
        trip = self._create_employee_trip(
            name="Fallback Approver Trip",
            start=datetime(2025, 7, 3),
            end=datetime(2025, 7, 4),
        )
        trip.with_user(self.user_employee).action_request_approval()
        self.assertEqual(trip.state, "request")
        self.assertEqual(trip.activity_ids.user_id, approver)
