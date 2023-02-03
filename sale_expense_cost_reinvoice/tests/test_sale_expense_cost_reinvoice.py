# Copyright 2021 Camptocamp SA (https://www.camptocamp.com).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests.common import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged("-at_install", "post_install")
class TestReInvoiceCost(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_expense_at_cost = cls.env["product.product"].create(
            {
                "name": "Expense Cost",
                "lst_price": 0,
                "expense_policy": "cost",
                "expense_mode": "auto",
            }
        )
        cls.order_at_cost = cls.env["sale.order"].create(
            {"partner_id": cls.partner_a.id},
        )
        cls.order_at_cost._create_analytic_account()
        cls.order_at_cost.action_confirm()
        cls.expense_sheet = cls.env["hr.expense.sheet"].create(
            {
                "name": "Expense Sheet",
                "employee_id": cls.expense_employee.id,
                "journal_id": cls.company_data["default_journal_purchase"].id,
                "accounting_date": fields.Date.today(),
            }
        )
        cls.expense_at_cost = cls.env["hr.expense"].create(
            {
                "sheet_id": cls.expense_sheet.id,
                "employee_id": cls.expense_employee.id,
                "name": "Expense At Cost",
                "date": fields.Date.today(),
                "product_id": cls.product_expense_at_cost.id,
                "total_amount": 550.0,
                "unit_amount": 0,
                "sale_order_id": cls.order_at_cost.id,
            }
        )

    def test_expense_at_cost_auto_reinvoice(self):
        self.expense_at_cost.analytic_account_id = (
            self.order_at_cost.analytic_account_id
        )
        self.expense_sheet.approve_expense_sheets()
        self.expense_sheet.action_sheet_move_create()
        self.assertEqual(
            self.expense_at_cost.total_amount,
            fields.first(self.order_at_cost.order_line).purchase_price,
            "Order line Cost should be the same as Expense Total amount",
        )
