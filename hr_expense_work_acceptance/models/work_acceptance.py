# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class WorkAcceptance(models.Model):
    _inherit = "work.acceptance"

    sheet_id = fields.Many2one(
        comodel_name="hr.expense.sheet",
        string="Expense Report",
        ondelete="set null",
        index=True,
        readonly=True,
        states={"draft": [("readonly", False)]},
    )

    @api.onchange("sheet_id")
    def _onchange_sheet_id(self):
        # WA from Expense shouldn't work with case WA from Purchase
        if self.env.context.get("default_purchase_id"):
            return
        self.partner_id = self.sheet_id.employee_id.user_partner_id
        self.company_id = self.sheet_id.company_id
        self.currency_id = self.sheet_id.currency_id
        self.date_due = self.sheet_id.expense_line_ids[:1].date
        wa_line_ids = [(5, 0, 0)]
        expenses = self.sheet_id.expense_line_ids.filtered(
            lambda l: l._get_product_qty() != 0
        )
        for line in expenses:
            wa_line_ids.append(
                (
                    0,
                    0,
                    {
                        "expense_id": line.id,
                        "name": line.name,
                        "product_uom": line.product_uom_id.id,
                        "product_id": line.product_id.id,
                        "price_unit": line.unit_amount,
                        "product_qty": line._get_product_qty(),
                    },
                )
            )
        self.wa_line_ids = wa_line_ids


class WorkAcceptanceLine(models.Model):
    _inherit = "work.acceptance.line"

    expense_id = fields.Many2one(
        comodel_name="hr.expense",
        string="Expense Line",
        ondelete="set null",
        index=True,
        readonly=False,
    )
