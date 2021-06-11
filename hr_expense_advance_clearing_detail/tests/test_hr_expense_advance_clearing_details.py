# Copyright 2019 Kitti Upariphutthiphong <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.exceptions import UserError
from odoo.tests import common
from odoo.tests.common import Form


class TestHrExpenseAdvanceClearingDetails(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal_bank = cls.env["account.journal"].search(
            [("type", "=", "bank")], limit=1
        )
        employee_home = cls.env["res.partner"].create({"name": "Employee Home Address"})
        group_ids = cls.env.ref("base.group_user").ids
        cls.test_user_1 = cls.env["res.users"].create(
            {"name": "John", "login": "test1", "groups_id": [(6, 0, group_ids)]}
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Employee A",
                "address_home_id": employee_home.id,
                "user_id": cls.test_user_1.id,
            }
        )
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

    def _create_expense(
        self,
        description,
        employee,
        product,
        amount,
        advance=False,
        payment_mode="own_account",
    ):
        with Form(self.env["hr.expense"]) as expense:
            expense.advance = advance
            expense.name = description
            expense.employee_id = employee
            expense.product_id = product
            expense.unit_amount = amount
            expense.payment_mode = payment_mode
        expense = expense.save()
        expense.tax_ids = False  # Test no vat
        return expense

    def _create_advance_detail(self, sheet, name, unit_amount):
        with Form(self.env["hr.expense.advance.line"]) as detail:
            detail.sheet_id = sheet
            detail.name = name
            detail.unit_amount = unit_amount
        return detail.save()

    def _register_payment(self, move_id, hr_return_advance=False):
        ctx = {
            "active_ids": [move_id.id],
            "active_id": move_id.id,
            "hr_return_advance": hr_return_advance,
            "active_model": "account.move",
        }
        PaymentWizard = self.env["account.payment.register"]
        with Form(PaymentWizard.with_context(ctx)) as f:
            f.journal_id = self.journal_bank
        payment_wizard = f.save()
        payment_wizard.action_create_payments()

    def test_01_clear_advance_with_details(self):
        # ------------------ Create Advance--------------------------
        advance_expense = self._create_expense(
            "Advance 1,000",
            self.employee,
            self.emp_advance,
            1000.0,
            advance=True,
        )
        res = advance_expense.action_submit_expenses()
        advance_sheet = self.env[res.get("res_model")].browse(res.get("res_id"))
        self.assertTrue(advance_sheet.advance)
        # create detail lines
        self._create_advance_detail(advance_sheet, "Detail 1", 100)
        detail_2 = self._create_advance_detail(advance_sheet, "Detail 2", 100)
        with self.assertRaises(UserError):
            advance_sheet.action_submit_sheet()
        detail_2.unit_amount = 900
        advance_sheet.action_submit_sheet()
        advance_sheet.approve_expense_sheets()
        advance_sheet.action_sheet_move_create()
        self.assertEqual(advance_sheet.clearing_residual, 1000.0)
        self._register_payment(advance_sheet.account_move_id)
        self.assertEqual(advance_sheet.state, "done")
        # ------------------ Clearing --------------------------
        # Clear this with previous advance
        vals = advance_sheet.open_clear_advance()  # Test Clear Advance button
        ctx = vals.get("context")
        self.assertEqual(ctx["default_advance_sheet_id"], advance_sheet.id)
        # Create clearing expense 1,000
        view_id = "hr_expense.view_hr_expense_sheet_form"
        with Form(self.env["hr.expense.sheet"], view=view_id) as clearing_sheet:
            clearing_sheet.name = "Clear Advance with Detail"
            clearing_sheet.employee_id = self.employee
            clearing_sheet.advance_sheet_id = advance_sheet
        clearing_sheet = clearing_sheet.save()
        self.assertEqual(clearing_sheet.total_amount, 1000.0)
        self.assertEqual(
            set(clearing_sheet.expense_line_ids.mapped("unit_amount")), {100, 900}
        )
