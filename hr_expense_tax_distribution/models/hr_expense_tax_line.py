# Copyright 2026 Akretion
# @author Guillaume MASSON <guillaume.masson@akretion.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class HrExpenseTaxLine(models.Model):
    """Distribution line linking one or more tax rates to a base (untaxed) amount.

    When a receipt contains goods subject to different VAT rates (e.g. a
    restaurant bill with 5.5 %, 10 % and 20 % items), this model lets the user
    split the expense total across as many distribution lines as needed.

    Each line carries one or more taxes (``tax_ids``) and a base amount
    (``base_amount_currency``).  Tax and total amounts are computed
    automatically.  The accounting entry is then generated from these lines
    instead of from the single ``tax_ids`` / ``total_amount`` pair on the parent
    expense.
    """

    _name = "hr.expense.tax.line"
    _description = "Expense Tax Distribution Line"
    _order = "sequence, id"

    expense_id = fields.Many2one(
        comodel_name="hr.expense",
        string="Expense",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    currency_id = fields.Many2one(
        related="expense_id.currency_id",
        store=True,
    )
    company_id = fields.Many2one(
        related="expense_id.company_id",
        store=True,
    )
    # Many2many: allows combining taxes on one line (e.g. VAT + eco-tax).
    # By default the onchange creates one line per tax in hr.expense.tax_ids;
    # the user can merge lines manually by adding taxes to an existing line.
    tax_ids = fields.Many2many(
        comodel_name="account.tax",
        string="Taxes",
        domain="[('company_id', '=', company_id), "
        "('type_tax_use', 'in', ['purchase', 'all'])]",
        check_company=True,
    )
    # Base amount in the expense currency (HT / tax-excluded)
    base_amount_currency = fields.Monetary(
        string="Base Amount (Tax Excl.)",
        currency_field="currency_id",
        required=True,
    )
    # Read-only computed fields -----------------------------------------------
    tax_amount_currency = fields.Monetary(
        string="Tax Amount",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )
    total_amount_currency = fields.Monetary(
        string="Total (Tax Incl.)",
        currency_field="currency_id",
        compute="_compute_amounts",
        store=True,
    )

    # -------------------------------------------------------------------------
    # Compute
    # -------------------------------------------------------------------------

    @api.depends(
        "tax_ids", "base_amount_currency", "currency_id", "expense_id.employee_id"
    )
    def _compute_amounts(self):
        for line in self:
            if not line.tax_ids or not line.base_amount_currency:
                line.tax_amount_currency = 0.0
                line.total_amount_currency = line.base_amount_currency
                continue
            partner = line.expense_id.employee_id.sudo().work_contact_id
            taxes = line.tax_ids.compute_all(
                line.base_amount_currency,
                currency=line.currency_id,
                partner=partner,
            )
            line.tax_amount_currency = taxes["total_included"] - taxes["total_excluded"]
            line.total_amount_currency = taxes["total_included"]

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    @api.constrains("base_amount_currency")
    def _check_base_amount_positive(self):
        for line in self:
            if line.base_amount_currency < 0:
                raise ValidationError(
                    _("The base amount on a tax distribution line cannot be negative.")
                )
