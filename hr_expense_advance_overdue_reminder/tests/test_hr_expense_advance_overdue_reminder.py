# Copyright 2020 Ecosoft Co., Ltd (http://ecosoft.co.th/)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html)

import time

from dateutil.relativedelta import relativedelta

from odoo import fields, tools
from odoo.exceptions import UserError
from odoo.modules.module import get_resource_path
from odoo.tests.common import Form, SavepointCase


class TestHrExpenseAdvanceOverdueReminder(SavepointCase):
    @classmethod
    def _load(cls, module, *args):
        tools.convert_file(
            cls.cr,
            module,
            get_resource_path(module, *args),
            {},
            "init",
            False,
            "test",
            cls.registry._assertion_report,
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._load("account", "test", "account_minimal_test.xml")
        cls.model_id = cls.env["ir.model"].search([("model", "=", "hr.expense.sheet")])
        cls.expense_model = cls.env["hr.expense"]
        cls.expense_sheet_model = cls.env["hr.expense.sheet"]
        cls.partner_1 = cls.env.ref("base.res_partner_12")
        cls.employee_1 = cls.env.ref("hr.employee_hne")
        cls.letter_report = cls.env.ref("base.report_ir_model_overview")
        cls.employee_1.address_home_id = cls.partner_1.id
        transfer_account = cls.browse_ref(cls, "account.transfer_account")
        cls.bank_journal = cls.browse_ref(cls, "account.bank_journal")
        cls.emp_advance = cls.env.ref("hr_expense_advance_clearing.product_emp_advance")
        cls.emp_advance.property_account_expense_id = transfer_account

        cls.sheet = cls._create_expense_sheet(
            cls, "Advance 1,000", cls.employee_1, cls.emp_advance, 1000.0, advance=True
        )
        date_today = fields.Date.from_string(time.strftime("%Y-05-05"))
        cls.sheet = cls.sheet.with_context({"date": date_today})

    def _create_expense(
        self,
        description,
        employee,
        product,
        amount,
        advance=False,
        payment_mode="own_account",
    ):
        with Form(self.expense_model) as expense:
            expense.advance = advance
            expense.name = description
            expense.employee_id = employee
            expense.product_id = product
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
        expense_sheet = self.expense_sheet_model.create(
            {
                "name": description,
                "employee_id": expense.employee_id.id,
                "expense_line_ids": [(6, 0, [expense.id])],
            }
        )
        return expense_sheet

    def _create_reminder_definition(self, reminder_type):
        hr_reminder = self.env["reminder.definition"].create(
            {
                "name": "HR Advance Definition",
                "model_id": self.model_id.id,
                "clearing_terms_days": 5,
                "create_activity": True,
                "activity_summary": "Summary Next",
                "activity_note": "Note something",
                "reminder_type": reminder_type,
                "attachment_letter": reminder_type == "mail" and True or False,
                "letter_report": self.letter_report.id,
            }
        )
        return hr_reminder

    def _register_payment(self, expense_sheet, hr_return_advance=False):
        ctx = {
            "active_ids": [expense_sheet.id],
            "active_id": expense_sheet.id,
            "hr_return_advance": hr_return_advance,
            "active_model": "hr.expense.sheet",
        }
        PaymentWizard = self.env["hr.expense.sheet.register.payment.wizard"]
        with Form(PaymentWizard.with_context(ctx)) as f:
            f.journal_id = self.bank_journal
        payment_wizard = f.save()
        payment_wizard.expense_post_payment()

    def _check_warnings(self, overdue):
        overdue.mail_subject = False
        with self.assertRaises(UserError):
            overdue.action_validate()
        overdue.write({"mail_subject": "Subject", "mail_body": False})
        with self.assertRaises(UserError):
            overdue.action_validate()
        overdue.mail_body = "Body"
        overdue.partner_id.email = False
        with self.assertRaises(UserError):
            overdue.action_validate()
        overdue.partner_id.email = "test_overdue@reminder.com"
        overdue.letter_report = False
        with self.assertRaises(UserError):
            overdue.action_validate()
        overdue.letter_report = self.env.ref("base.report_ir_model_overview").id

    def _check_normal_process(self, reminder_type):
        today = fields.Date.today()
        self.assertIn("EXAV", self.sheet.number)
        self.assertEqual(self.sheet.state, "draft")
        self.sheet.action_submit_sheet()
        self.assertEqual(self.sheet.state, "submit")
        self.sheet.approve_expense_sheets()
        self.assertEqual(self.sheet.state, "approve")
        self.assertFalse(self.sheet.clearing_date_due)
        with self.assertRaises(UserError):
            self.sheet.action_sheet_move_create()
        self._create_reminder_definition(reminder_type)
        self.sheet.action_sheet_move_create()
        self.assertEqual(self.sheet.state, "post")
        self.assertEqual(self.sheet.clearing_date_due, today + relativedelta(days=5))
        # check state != done should not create wizard overdue
        with self.assertRaises(UserError):
            self.sheet.action_overdue_reminder()
        self._register_payment(self.sheet)
        self.assertEqual(self.sheet.state, "done")

    def test_01_reminder_email(self):
        self._check_normal_process("mail")
        # Overdue date configured due date < today 1 day
        self.sheet.clearing_date_due = fields.Date.from_string(
            time.strftime("%Y-05-04")
        )
        self.assertTrue(self.sheet.overdue)
        self.assertFalse(self.sheet.overdue_reminder_last_date)
        self.assertFalse(self.sheet.overdue_reminder_counter)
        self.sheet.address_id = self.partner_1.id
        ctx = self.sheet._context.copy()
        ctx.update({"active_ids": [self.sheet.id], "active_model": "hr.expense.sheet"})
        action = self.sheet.with_context(ctx).action_overdue_reminder()
        with Form(self.env[action["res_model"]].with_context(action["context"])) as f:
            wizard = f.save()
        action = wizard.run()
        overdue = self.env[action["res_model"]].search(action["domain"])
        self.assertEqual(overdue.state, "draft")
        activity_type = self.env["mail.activity.type"].search([], limit=1)
        overdue.activity_type_id = activity_type.id
        # check case delete mail subject or mail description
        self._check_warnings(overdue)
        overdue.action_validate()
        self.assertEqual(overdue.state, "done")
        self.assertEqual(overdue.expense_sheet_ids.overdue_reminder_counter, 1)
        # check mail send
        view_mail = overdue.action_get_mail_view()
        mail_object = self.env[view_mail["res_model"]].search(view_mail["domain"])
        self.assertEqual(overdue.mail_count, len(mail_object))
        # filter this expense again, should be error
        with self.assertRaises(UserError):
            wizard.run()
        wizard.min_interval_days = 0
        with self.assertRaises(UserError):
            wizard.run()
        overdue.action_cancel()
        self.assertEqual(overdue.state, "cancel")

    def test_02_reminder_letter(self):
        self._check_normal_process("letter")
        self.sheet.clearing_date_due = fields.Date.from_string(
            time.strftime("%Y-05-04")
        )
        self.sheet.address_id = self.partner_1.id
        ctx = self.sheet._context.copy()
        ctx.update({"active_ids": [self.sheet.id], "active_model": "hr.expense.sheet"})
        action = self.sheet.with_context(ctx).action_overdue_reminder()
        # Test with case no overdue_sheet_ids
        action["context"].get("overdue_sheet_ids").pop()
        with Form(self.env[action["res_model"]].with_context(action["context"])) as f:
            wizard = f.save()
        action = wizard.run()
        overdue = self.env[action["res_model"]].search(action["domain"])
        self.assertEqual(overdue.state, "draft")
        activity_type = self.env["mail.activity.type"].search([], limit=1)
        overdue.activity_type_id = activity_type.id
        action = overdue.action_validate()
        self.assertEqual(overdue.state, "done")
        self.assertEqual(overdue.expense_sheet_ids.overdue_reminder_counter, 1)
        self.assertEqual(action.get("report_type", False), "qweb-pdf")
