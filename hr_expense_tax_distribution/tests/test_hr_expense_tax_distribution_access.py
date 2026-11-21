# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase, new_test_user

from odoo.addons.base.tests.common import DISABLED_MAIL_CONTEXT


@tagged("post_install", "-at_install")
class TestHrExpenseTaxDistributionAccess(TransactionCase):
    """A plain employee must reach the distribution lines of their own expense.

    hr_expense grants hr.expense itself to base.group_user, so an employee with
    no expense group at all files their own expenses. The distribution lines are
    part of that document, so they need the same reach -- scoped to their own
    records by the rules in security/hr_expense_tax_line_rules.xml.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, **DISABLED_MAIL_CONTEXT))
        cls.company = cls.env.company

        def _make_tax(name, amount):
            return cls.env["account.tax"].create(
                {
                    "name": name,
                    "type_tax_use": "purchase",
                    "amount_type": "percent",
                    "amount": amount,
                    "price_include": False,
                    "company_id": cls.company.id,
                }
            )

        cls.tax_10 = _make_tax("TVA 10%", 10.0)
        cls.tax_20 = _make_tax("TVA 20%", 20.0)

        cls.product = cls.env["product.product"].search(
            [("can_be_expensed", "=", True)], limit=1
        )
        if not cls.product:
            cls.product = cls.env["product.product"].create(
                {"name": "Generic Expense", "can_be_expensed": True}
            )
        cls.product.supplier_taxes_id = False

        # Deliberately no expense group: base.group_user only.
        cls.user = new_test_user(
            cls.env, login="tax-dist-employee", groups="base.group_user"
        )
        cls.employee = cls.env["hr.employee"].create(
            {"name": "Tax Dist Employee", "user_id": cls.user.id}
        )
        cls.other_user = new_test_user(
            cls.env, login="tax-dist-other", groups="base.group_user"
        )
        cls.other_employee = cls.env["hr.employee"].create(
            {"name": "Other Employee", "user_id": cls.other_user.id}
        )

    def _expense_with_line(self, employee):
        expense = self.env["hr.expense"].create(
            {
                "name": "Restaurant",
                "employee_id": employee.id,
                "product_id": self.product.id,
                "total_amount_currency": 100.0,
                "company_id": self.company.id,
                "tax_ids": [Command.set((self.tax_10 | self.tax_20).ids)],
            }
        )
        expense.write(
            {"tax_line_ids": expense._sync_tax_distribution_lines(self.tax_10)}
        )
        return expense

    def test_employee_reads_own_distribution_lines(self):
        """Reading an own expense that has lines must not raise."""
        expense = self._expense_with_line(self.employee)
        # The one2many is only fetched from the database on a cold cache, which
        # is what an HTTP request has. Without this the read is served from the
        # cache and passes even when the access rights are missing, so do not
        # drop it: it is the whole point of the regression.
        self.env.invalidate_all()
        expense_as_user = expense.with_user(self.user)
        self.assertTrue(expense_as_user.read(["tax_line_ids"]))
        self.assertEqual(len(expense_as_user.tax_line_ids), 1)

    def test_employee_creates_distribution_lines(self):
        """Picking more than one tax creates the lines, as the employee."""
        expense_form = Form(self.env["hr.expense"].with_user(self.user))
        expense_form.name = "Restaurant"
        expense_form.product_id = self.product
        expense_form.total_amount_currency = 100.0
        expense_form.tax_ids.add(self.tax_10)
        expense_form.tax_ids.add(self.tax_20)
        expense = expense_form.save()
        self.assertEqual(len(expense.tax_line_ids), 2)

    def test_employee_removes_a_distribution_line(self):
        """Dropping back to a single tax unlinks the lines, as the employee."""
        expense = self._expense_with_line(self.employee).with_user(self.user)
        expense.write({"tax_ids": [Command.set(self.tax_10.ids)]})
        expense.write({"tax_line_ids": [Command.clear()]})
        self.assertFalse(expense.tax_line_ids)

    def test_employee_does_not_see_other_employees_lines(self):
        """The record rule keeps employees out of each other's lines."""
        other_expense = self._expense_with_line(self.other_employee)
        other_line = other_expense.tax_line_ids
        self.assertTrue(other_line)
        self.env.invalidate_all()
        found = (
            self.env["hr.expense.tax.line"]
            .with_user(self.user)
            .search([("id", "in", other_line.ids)])
        )
        self.assertFalse(found)
        with self.assertRaises(AccessError):
            other_line.with_user(self.user).read(["base_amount_currency"])
