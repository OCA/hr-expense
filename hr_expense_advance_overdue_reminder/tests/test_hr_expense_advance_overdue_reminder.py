# Copyright 2023 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

from freezegun import freeze_time

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import Form, TransactionCase


class TestHrExpenseAdvanceOverdueReminder(TransactionCase):
    @classmethod
    @freeze_time("2001-01-01")
    def setUpClass(cls):
        super().setUpClass()
        cls.reminder_config = cls.env["reminder.definition"]
        cls.overdue_wizard = cls.env["hr.advance.overdue.reminder.wizard"]
        cls.mail_compose = cls.env["mail.compose.message"]
        cls.journal_bank = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        cls.letter_report = cls.env["ir.actions.report"].search([], limit=1)
        employee_home = cls.env["res.partner"].create({"name": "Employee Home Address"})
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Employee A", "address_home_id": employee_home.id}
        )
        # Advance product
        advance_account = cls.env["account.account"].create(
            {
                "code": "154000",
                "name": "Employee Advance",
                "user_type_id": cls.env.ref(
                    "account.data_account_type_current_assets"
                ).id,
                "reconcile": True,
            }
        )
        cls.emp_advance = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        cls.emp_advance.property_account_expense_id = advance_account
        # Create advance expense 1,000
        cls.advance = cls._create_expense_sheet(
            cls, "Advance 1,000", cls.employee, cls.emp_advance, 1000.0, advance=True
        )

    def _create_expense(
        self,
        description,
        employee,
        product,
        amount,
        advance=False,
        payment_mode="own_account",
        account=False,
    ):
        with Form(
            self.env["hr.expense"].with_context(default_advance=advance)
        ) as expense:
            expense.name = description
            expense.employee_id = employee
            expense.unit_amount = amount
            expense.payment_mode = payment_mode
        expense = expense.save()
        expense.tax_ids = False  # Test no vat
        return expense

    def _create_expense_sheet(
        self, description, employee, product, amount, advance=False
    ):
        expense = self._create_expense(
            self, description, employee, product, amount, advance
        )
        # Add expense to expense sheet
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": description,
                "advance": advance,
                "employee_id": expense.employee_id.id,
                "expense_line_ids": [(6, 0, [expense.id])],
            }
        )
        return expense_sheet

    def _register_payment(self, move_id, amount, ctx=False, hr_return_advance=False):
        ctx = ctx or {
            "active_ids": [move_id.id],
            "active_id": move_id.id,
            "active_model": "account.move",
        }
        ctx["hr_return_advance"] = hr_return_advance
        PaymentWizard = self.env["account.payment.register"]
        with Form(PaymentWizard.with_context(**ctx)) as f:
            f.journal_id = self.journal_bank
            f.payment_date = fields.Date.today()
            f.amount = amount
        payment_wizard = f.save()
        payment_wizard.action_create_payments()

    @freeze_time("2001-01-01")
    def test_01_reminder_advance(self):
        # Overdue date configured due date < today 1 day
        self.assertFalse(self.advance.clearing_date_due)
        self.assertEqual(self.advance.state, "draft")
        # Change clearing due date less than today, it should error
        with self.assertRaises(UserError):
            with Form(self.advance) as av:
                av.clearing_date_due = "2000-01-01"
        self.advance.clearing_date_due = False
        self.advance.action_submit_sheet()
        self.advance.approve_expense_sheets()
        # Clearing Due Date is not selected, it will default from reminder config
        with self.assertRaises(UserError):
            self.advance.action_sheet_move_create()
        reminder = self.reminder_config.create({"name": "Overdue Reminder"})
        self.assertEqual(reminder.clearing_terms_days, 30)
        self.advance.action_sheet_move_create()
        self.assertEqual(
            self.advance.clearing_date_due.strftime("%Y-%m-%d"), "2001-01-31"
        )
        self.assertFalse(self.advance.is_overdue)
        self.assertEqual(self.advance.clearing_residual, 1000.0)
        self._register_payment(self.advance.account_move_id, 1000.0)
        self.assertEqual(self.advance.state, "done")
        # Check Overdue Advance
        with self.assertRaises(UserError):
            self.advance.action_overdue_reminder()
        self.advance.clearing_date_due = "2000-12-31"
        self.assertTrue(self.advance.is_overdue)
        result = self.advance.action_overdue_reminder()
        # Open wizard overdue reminder
        self.assertEqual(result["res_model"], "hr.advance.overdue.reminder.wizard")
        with Form(
            self.overdue_wizard.with_context(
                active_ids=self.advance.ids,
                default_employee_ids=self.advance.employee_id.ids,
                default_reminder_definition_id=reminder.id,
            )
        ) as wiz:
            wiz.reminder_number = 5
        wizard_reminder = wiz.save()
        self.assertTrue(wizard_reminder.employee_ids)
        action = wizard_reminder.with_context(active_ids=False).run()
        self.assertFalse(action["domain"][0][2])
        action = wizard_reminder.run()
        self.assertTrue(action["domain"][0][2])
        advance_overdue_reminder = self.env["hr.advance.overdue.reminder"].browse(
            action["domain"][0][2]
        )
        self.assertEqual(advance_overdue_reminder.state, "draft")
        # Test reminder by letter
        with Form(advance_overdue_reminder) as av_overdue:
            av_overdue.create_activity = True
            av_overdue.reminder_definition_id = reminder
            av_overdue.reminder_type = "letter"
        self.assertFalse(av_overdue.letter_report)
        with self.assertRaises(UserError):
            advance_overdue_reminder.action_validate()
        self.letter_report.model = "hr.advance.overdue.reminder"
        with Form(advance_overdue_reminder) as av_overdue:
            av_overdue.letter_report = self.letter_report
        advance_overdue_reminder.action_validate()
        self.assertEqual(advance_overdue_reminder.state, "done")
        # Check name report
        name_report = advance_overdue_reminder._get_report_base_filename()
        self.assertEqual(name_report, "overdue_letter-Employee_A")
        # Test reminder by email
        advance_overdue_reminder.state = "draft"
        with Form(advance_overdue_reminder) as av_overdue:
            av_overdue.reminder_type = "mail"
        # Check employee address private, not allow send email
        advance_overdue_reminder.employee_id.address_home_id.type = "private"
        with self.assertRaises(UserError):
            advance_overdue_reminder.action_validate()
        advance_overdue_reminder.employee_id.address_home_id.type = "contact"
        mail_compose = advance_overdue_reminder.action_validate()
        with Form(
            self.mail_compose.with_context(
                active_ids=mail_compose["context"].get("active_ids"),
                default_model=mail_compose["context"].get("default_model"),
                default_res_id=mail_compose["context"].get("default_res_id"),
                default_template_id=mail_compose["context"].get("default_template_id"),
            )
        ) as wiz:
            wiz.body = "Test"
        mail_wizard = wiz.save()
        mail_wizard._action_send_mail()
        self.assertEqual(advance_overdue_reminder.state, "done")
        with self.assertRaises(UserError):
            advance_overdue_reminder.unlink()
        advance_overdue_reminder.action_cancel()
        self.assertEqual(advance_overdue_reminder.state, "cancel")
        advance_overdue_reminder.state = "draft"
        advance_overdue_reminder.create_activity = True
        advance_overdue_reminder.activity_scheduled_date = "2001-01-15"
        advance_overdue_reminder.activity_user_id = self.env.user.id
        mail_compose = advance_overdue_reminder.action_validate()
        with Form(
            self.mail_compose.with_context(
                active_ids=mail_compose["context"].get("active_ids"),
                default_model=mail_compose["context"].get("default_model"),
                default_res_id=mail_compose["context"].get("default_res_id"),
                default_template_id=mail_compose["context"].get("default_template_id"),
            )
        ) as wiz:
            wiz.body = "Test"
        mail_wizard = wiz.save()
        mail_wizard._action_send_mail()
        self.assertEqual(advance_overdue_reminder.state, "done")
        # Check reminder < today
        self.advance.reminder_next_time = "2000-12-31"
        self.assertTrue(self.advance.is_overdue)
