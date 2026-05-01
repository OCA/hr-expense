# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestHrExpenseTaxDistribution(TransactionCase):
    """Tests for hr_expense_tax_distribution.

    Main scenario: a restaurant receipt (86.75 EUR TTC) with three VAT rates:
      - Food:              base 50.00, tax 5.5%  → tax  2.75, total  52.75
      - Soft drinks:       base 20.00, tax 10%   → tax  2.00, total  22.00
      - Alcoholic drinks:  base 10.00, tax 20%   → tax  2.00, total  12.00
      Total TTC: 86.75
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company = cls.env.company
        cls.currency = cls.company.currency_id

        # Taxes (purchase, percent, price-excluded)
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

        cls.tax_5 = _make_tax("TVA 5.5%", 5.5)
        cls.tax_10 = _make_tax("TVA 10%", 10.0)
        cls.tax_20 = _make_tax("TVA 20%", 20.0)
        cls.tax_eco = _make_tax("Eco-tax 2%", 2.0)

        # Employee
        cls.employee = cls.env["hr.employee"].create({"name": "Test Employee"})

        # Product (generic expense)
        cls.product = cls.env["product.product"].search(
            [("can_be_expensed", "=", True)], limit=1
        )
        if not cls.product:
            cls.product = cls.env["product.product"].create(
                {"name": "Generic Expense", "can_be_expensed": True}
            )
        cls.product.supplier_taxes_id = False

        # Product with fixed cost (product_has_cost = True) for quantity tests
        cls.product_with_cost = cls.env["product.product"].create(
            {
                "name": "Expense With Cost",
                "can_be_expensed": True,
                "standard_price": 10.0,
            }
        )

    def _make_expense(
        self, total_amount_currency, tax_ids=None, product=None, quantity=1.0
    ):
        vals = {
            "name": "Restaurant Test",
            "employee_id": self.employee.id,
            "product_id": (product or self.product).id,
            "total_amount_currency": total_amount_currency,
            "quantity": quantity,
            "company_id": self.company.id,
        }
        if tax_ids is not None:
            vals["tax_ids"] = [Command.set(tax_ids.ids)]
        return self.env["hr.expense"].create(vals)

    def _make_dist_lines(self, expense, specs):
        """Helper: create distribution lines by calling _sync_tax_distribution_lines
        with an explicit base amount per tax.

        ``specs`` is a list of (tax_recordset, base_amount) tuples.
        This helper calls _sync_tax_distribution_lines to create the initial
        lines (zero base), then sets the base amounts individually, keeping
        the helper in sync with the real creation code path.
        """
        taxes = self.env["account.tax"]
        base_by_tax = {}
        for tax_rs, base in specs:
            taxes |= tax_rs
            base_by_tax[tax_rs.id] = base

        commands = expense._sync_tax_distribution_lines(taxes)
        expense.write({"tax_line_ids": commands})

        # Set base amounts after creation (lines start at 0.0)
        for line in expense.tax_line_ids:
            if len(line.tax_ids) == 1 and line.tax_ids.id in base_by_tax:
                line.base_amount_currency = base_by_tax[line.tax_ids.id]

        return expense.tax_line_ids

    # ------------------------------------------------------------------
    # 1. Distribution line computation
    # ------------------------------------------------------------------

    def test_single_tax_compute_amounts(self):
        """Tax and total amounts computed correctly for a single tax on a line."""
        expense = self._make_expense(22.0)
        line = self.env["hr.expense.tax.line"].create(
            {
                "expense_id": expense.id,
                "tax_ids": [Command.set(self.tax_10.ids)],
                "base_amount_currency": 20.0,
            }
        )
        self.assertAlmostEqual(line.tax_amount_currency, 2.0, places=2)
        self.assertAlmostEqual(line.total_amount_currency, 22.0, places=2)

    def test_multi_tax_on_one_line(self):
        """Two taxes on a single distribution line are cumulated correctly."""
        expense = self._make_expense(100.0)
        # 10% + 2% eco-tax on 80 EUR base → tax = 9.6, total = 89.6
        line = self.env["hr.expense.tax.line"].create(
            {
                "expense_id": expense.id,
                "tax_ids": [Command.set((self.tax_10 | self.tax_eco).ids)],
                "base_amount_currency": 80.0,
            }
        )
        # 80 * (1 + 0.10 + 0.02) = 89.6
        self.assertAlmostEqual(line.tax_amount_currency, 9.6, places=2)
        self.assertAlmostEqual(line.total_amount_currency, 89.6, places=2)

    def test_zero_base_gives_zero_amounts(self):
        """A line with base_amount_currency = 0 computes 0 for all amounts."""
        expense = self._make_expense(86.75)
        line = self.env["hr.expense.tax.line"].create(
            {
                "expense_id": expense.id,
                "tax_ids": [Command.set(self.tax_20.ids)],
                "base_amount_currency": 0.0,
            }
        )
        self.assertEqual(line.tax_amount_currency, 0.0)
        self.assertEqual(line.total_amount_currency, 0.0)

    def test_no_tax_on_line(self):
        """A line with no tax_ids computes 0 tax and total = base."""
        expense = self._make_expense(50.0)
        line = self.env["hr.expense.tax.line"].create(
            {
                "expense_id": expense.id,
                "tax_ids": [],
                "base_amount_currency": 50.0,
            }
        )
        self.assertEqual(line.tax_amount_currency, 0.0)
        self.assertAlmostEqual(line.total_amount_currency, 50.0, places=2)

    # ------------------------------------------------------------------
    # 2. has_tax_distribution flag
    # ------------------------------------------------------------------

    def test_has_tax_distribution_true(self):
        expense = self._make_expense(86.75)
        self._make_dist_lines(expense, [(self.tax_5, 50.0)])
        expense.invalidate_recordset()
        self.assertTrue(expense.has_tax_distribution)

    def test_has_tax_distribution_false_when_no_lines(self):
        expense = self._make_expense(50.0)
        self.assertFalse(expense.has_tax_distribution)

    # ------------------------------------------------------------------
    # 3. Onchange: lines generated only when tax_ids has 2+ taxes
    #    All onchange tests use Form to simulate real UI interactions.
    # ------------------------------------------------------------------

    def test_onchange_single_tax_no_lines(self):
        """Adding a single tax via the form must not create distribution lines."""
        with Form(self.env["hr.expense"]) as f:
            f.name = "Restaurant Test"
            f.employee_id = self.employee
            f.product_id = self.product
            f.total_amount_currency = 50.0
            f.tax_ids.add(self.tax_10)
        expense = f.save()
        self.assertFalse(expense.tax_line_ids)

    def test_onchange_two_taxes_creates_two_lines(self):
        """Adding two taxes via the form creates one distribution line per tax."""
        with Form(self.env["hr.expense"]) as f:
            f.name = "Restaurant Test"
            f.employee_id = self.employee
            f.product_id = self.product
            f.total_amount_currency = 74.75
            f.tax_ids.add(self.tax_5)
            f.tax_ids.add(self.tax_10)
        expense = f.save()
        self.assertEqual(len(expense.tax_line_ids), 2)
        line_taxes = expense.tax_line_ids.mapped("tax_ids")
        self.assertIn(self.tax_5, line_taxes)
        self.assertIn(self.tax_10, line_taxes)

    def test_onchange_three_taxes_creates_three_lines(self):
        """Adding three taxes creates three distribution lines (main scenario)."""
        with Form(self.env["hr.expense"]) as f:
            f.name = "Restaurant Test"
            f.employee_id = self.employee
            f.product_id = self.product
            f.total_amount_currency = 86.75
            f.tax_ids.add(self.tax_5)
            f.tax_ids.add(self.tax_10)
            f.tax_ids.add(self.tax_20)
        expense = f.save()
        self.assertEqual(len(expense.tax_line_ids), 3)

    def test_onchange_removing_tax_to_single_clears_all_lines(self):
        """Removing taxes until only one remains must clear all distribution lines."""
        # Create with 3 taxes
        with Form(self.env["hr.expense"]) as f:
            f.name = "Restaurant Test"
            f.employee_id = self.employee
            f.product_id = self.product
            f.total_amount_currency = 86.75
            f.tax_ids.add(self.tax_5)
            f.tax_ids.add(self.tax_10)
            f.tax_ids.add(self.tax_20)
        expense = f.save()
        self.assertEqual(len(expense.tax_line_ids), 3)

        # Remove two taxes via the form, leaving only one
        with Form(expense) as f:
            f.tax_ids.remove(index=0)  # removes first tax in the list
            f.tax_ids.remove(index=0)  # removes second tax (now index 0)
        expense = f.save()
        self.assertFalse(
            expense.tax_line_ids,
            "All distribution lines must be cleared when only one tax remains.",
        )

    def test_onchange_adding_tax_preserves_existing_base_amounts(self):
        """Adding a new tax to an expense that already has distribution lines
        must preserve the base_amount_currency of the existing lines."""
        # Start with two taxes and fill in base amounts
        with Form(self.env["hr.expense"]) as f:
            f.name = "Restaurant Test"
            f.employee_id = self.employee
            f.product_id = self.product
            f.total_amount_currency = 86.75
            f.tax_ids.add(self.tax_5)
            f.tax_ids.add(self.tax_10)
        expense = f.save()

        for line in expense.tax_line_ids:
            if self.tax_5 in line.tax_ids:
                line.base_amount_currency = 50.0
            elif self.tax_10 in line.tax_ids:
                line.base_amount_currency = 20.0

        # Add a third tax via the form
        with Form(expense) as f:
            f.tax_ids.add(self.tax_20)
        expense = f.save()

        self.assertEqual(len(expense.tax_line_ids), 3)
        for line in expense.tax_line_ids:
            if self.tax_5 in line.tax_ids:
                self.assertAlmostEqual(line.base_amount_currency, 50.0)
            elif self.tax_10 in line.tax_ids:
                self.assertAlmostEqual(line.base_amount_currency, 20.0)
            elif self.tax_20 in line.tax_ids:
                # Newly added line must start at 0
                self.assertAlmostEqual(line.base_amount_currency, 0.0)

    def test_onchange_removing_one_tax_preserves_other_base_amounts(self):
        """Removing one tax (while 2+ remain) must keep the base amounts of
        the surviving lines intact."""
        with Form(self.env["hr.expense"]) as f:
            f.name = "Restaurant Test"
            f.employee_id = self.employee
            f.product_id = self.product
            f.total_amount_currency = 86.75
            f.tax_ids.add(self.tax_5)
            f.tax_ids.add(self.tax_10)
            f.tax_ids.add(self.tax_20)
        expense = f.save()

        for line in expense.tax_line_ids:
            if self.tax_5 in line.tax_ids:
                line.base_amount_currency = 50.0
            elif self.tax_10 in line.tax_ids:
                line.base_amount_currency = 20.0
            elif self.tax_20 in line.tax_ids:
                line.base_amount_currency = 10.0

        # Remove tax_20 from the form, two taxes remain
        with Form(expense) as f:
            f.tax_ids.remove(self.tax_20.id)
        expense = f.save()

        self.assertEqual(len(expense.tax_line_ids), 2)
        for line in expense.tax_line_ids:
            if self.tax_5 in line.tax_ids:
                self.assertAlmostEqual(line.base_amount_currency, 50.0)
            elif self.tax_10 in line.tax_ids:
                self.assertAlmostEqual(line.base_amount_currency, 20.0)

    # ------------------------------------------------------------------
    # 4. Expense-level tax amounts derived from distribution lines
    # ------------------------------------------------------------------

    def test_expense_tax_amounts_from_distribution(self):
        """tax_amount_currency and untaxed_amount_currency on hr.expense
        reflect the distribution lines once base amounts are non-zero."""
        expense = self._make_expense(86.75)
        self._make_dist_lines(
            expense,
            [
                (self.tax_5, 50.0),  # tax 2.75, total 52.75
                (self.tax_10, 20.0),  # tax 2.00, total 22.00
                (self.tax_20, 10.0),  # tax 2.00, total 12.00
            ],
        )
        expense.invalidate_recordset()
        self.assertAlmostEqual(expense.tax_amount_currency, 6.75, places=2)
        self.assertAlmostEqual(expense.untaxed_amount_currency, 80.0, places=2)

    def test_expense_tax_amounts_standard_when_lines_all_zero(self):
        """When all distribution lines have base_amount = 0, standard Odoo
        computation is used for tax_amount_currency (not overridden)."""
        expense = self._make_expense(120.0, tax_ids=self.tax_20)
        # Create a single line but leave base at 0
        self.env["hr.expense.tax.line"].create(
            {
                "expense_id": expense.id,
                "tax_ids": [Command.set(self.tax_20.ids)],
                "base_amount_currency": 0.0,
            }
        )
        expense.invalidate_recordset()
        # Standard: 120 TTC at 20% → tax = 20.0, untaxed = 100.0
        self.assertAlmostEqual(expense.tax_amount_currency, 20.0, places=2)

    # ------------------------------------------------------------------
    # 5. Constraint: total must match
    # ------------------------------------------------------------------

    def test_constraint_total_matches(self):
        """No ValidationError when distribution totals equal expense total."""
        expense = self._make_expense(86.75)
        self._make_dist_lines(
            expense,
            [(self.tax_5, 50.0), (self.tax_10, 20.0), (self.tax_20, 10.0)],
        )
        expense._check_tax_distribution_total()  # must not raise

    def test_constraint_total_mismatch_raises(self):
        expense = self._make_expense(100.0)
        self._make_dist_lines(expense, [(self.tax_20, 10.0)])  # total = 12, not 100
        with self.assertRaises(ValidationError):
            expense._check_tax_distribution_total()

    def test_no_constraint_when_no_lines(self):
        expense = self._make_expense(100.0)
        expense._check_tax_distribution_total()  # must not raise

    def test_no_constraint_when_total_is_zero(self):
        expense = self._make_expense(0.0)
        self.env["hr.expense.tax.line"].create(
            {
                "expense_id": expense.id,
                "tax_ids": [Command.set(self.tax_20.ids)],
                "base_amount_currency": 0.0,
            }
        )
        expense._check_tax_distribution_total()  # must not raise

    # ------------------------------------------------------------------
    # 6. Constraint: base_amount cannot be negative
    # ------------------------------------------------------------------

    def test_constraint_negative_base_raises(self):
        expense = self._make_expense(10.0)
        with self.assertRaises(ValidationError):
            self.env["hr.expense.tax.line"].create(
                {
                    "expense_id": expense.id,
                    "tax_ids": [Command.set(self.tax_20.ids)],
                    "base_amount_currency": -5.0,
                }
            )

    # ------------------------------------------------------------------
    # 7. Move line vals: price_unit and quantity
    # ------------------------------------------------------------------

    def test_move_lines_price_unit_quantity_1(self):
        """Without product_has_cost, quantity=1 and price_unit=total_amount (TTC)."""
        expense = self._make_expense(86.75, product=self.product)
        self._make_dist_lines(
            expense,
            [(self.tax_5, 50.0), (self.tax_10, 20.0), (self.tax_20, 10.0)],
        )
        lines = expense._get_tax_distribution_move_lines_vals()
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertEqual(line["quantity"], 1.0)
            # price_unit must be total_amount_currency (TTC) of each dist line
            # 5.5%: 50 * 1.055 = 52.75 / 10%: 20 * 1.10 = 22.0 / 20%: 10 * 1.20 = 12.0
            self.assertIn(round(line["price_unit"], 2), [52.75, 22.0, 12.0])

    def test_move_lines_price_unit_with_quantity(self):
        """With product_has_cost and quantity=2, price_unit = total_ttc / 2."""
        # 40 HT * 1.10 = 44.0 TTC → price_unit = 44.0 / 2 = 22.0
        expense = self._make_expense(44.0, product=self.product_with_cost, quantity=2.0)
        self._make_dist_lines(expense, [(self.tax_10, 40.0)])
        lines = expense._get_tax_distribution_move_lines_vals()
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["quantity"], 2.0)
        self.assertAlmostEqual(lines[0]["price_unit"], 22.0, places=2)

    def test_move_lines_account_move_amounts(self):
        """End-to-end: the generated account.move has the correct base and tax
        amounts for each distribution line (own_account flow)."""
        expense = self._make_expense(
            86.75,
            tax_ids=self.tax_5 | self.tax_10 | self.tax_20,
            product=self.product,
        )
        self._make_dist_lines(
            expense,
            [(self.tax_5, 50.0), (self.tax_10, 20.0), (self.tax_20, 10.0)],
        )
        sheet_act = expense.action_submit_expenses()
        sheet = self.env[sheet_act["res_model"]].browse(sheet_act["res_id"])
        sheet.action_submit_sheet()
        sheet.action_approve_expense_sheets()
        sheet.action_sheet_move_post()
        move = self.env["account.move"].search(
            [("expense_sheet_id", "=", sheet.id)], limit=1
        )
        self.assertTrue(move)
        # Collect product lines (display_type = 'product') and tax lines
        product_lines = move.line_ids.filtered(lambda ml: ml.display_type == "product")
        tax_lines = move.line_ids.filtered(lambda ml: ml.display_type == "tax")
        self.assertEqual(
            len(product_lines), 3, "One product line per distribution entry"
        )
        self.assertEqual(len(tax_lines), 3, "One tax line per distribution entry")
        # Total TTC on the move must equal expense total
        self.assertAlmostEqual(move.amount_total, 86.75, places=2)
        # HT sum: 50 + 20 + 10 = 80
        self.assertAlmostEqual(move.amount_untaxed, 80.0, places=2)
        # Tax sum: 2.75 + 2.00 + 2.00 = 6.75
        self.assertAlmostEqual(move.amount_tax, 6.75, places=2)
