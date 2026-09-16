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
        # Needed to create sale.order records below
        cls.env.user.group_ids |= cls.env.ref("sales_team.group_sale_salesman")
        cls.product_expense_at_cost = cls.env["product.product"].create(
            {
                "name": "Expense Cost",
                "lst_price": 0,
                "expense_policy": "cost",
                "expense_mode": "auto",
                "taxes_id": [(6, 0, [])],
                "supplier_taxes_id": [(6, 0, [])],
            }
        )
        cls.order_at_cost = cls.env["sale.order"].create(
            {"partner_id": cls.partner_a.id},
        )
        cls.order_at_cost.action_confirm()
        cls.expense_at_cost = cls.env["hr.expense"].create(
            {
                "employee_id": cls.expense_employee.id,
                "name": "Expense At Cost",
                "date": fields.Date.today(),
                "product_id": cls.product_expense_at_cost.id,
                "total_amount": 550.0,
                "sale_order_id": cls.order_at_cost.id,
            }
        )

    def test_expense_at_cost_auto_reinvoice(self):
        self.expense_at_cost.action_approve()
        self.post_expenses_with_wizard(
            self.expense_at_cost,
            journal=self.company_data["default_journal_purchase"],
            date=fields.Date.today(),
        )
        self.assertEqual(
            self.expense_at_cost.total_amount,
            self.order_at_cost.order_line[:1].purchase_price,
            "Order line Cost should be the same as Expense Total amount",
        )
