# Copyright 2021 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class HRExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    wa_count = fields.Integer(compute="_compute_wa_ids", string="WA count", default=0)
    wa_ids = fields.One2many(
        comodel_name="work.acceptance",
        compute="_compute_wa_ids",
        string="Work Acceptances",
    )
    wa_line_ids = fields.One2many(
        comodel_name="work.acceptance.line",
        inverse_name="expense_id",
        string="WA Lines",
        readonly=True,
    )
    wa_accepted = fields.Boolean(string="WA Accepted", compute="_compute_wa_accepted")

    def _compute_wa_ids(self):
        for sheet in self:
            sheet.wa_ids = sheet.expense_line_ids.mapped("wa_line_ids").mapped("wa_id")
            sheet.wa_count = len(sheet.wa_ids)

    def _compute_wa_accepted(self):
        for sheet in self:
            lines = sheet.expense_line_ids.filtered(lambda l: l.qty_to_accept > 0)
            sheet.wa_accepted = not any(lines)

    def action_view_wa(self):
        self.ensure_one()
        act = self.env.ref("purchase_work_acceptance.action_work_acceptance")
        result = act.sudo().read()[0]
        create_wa = self.env.context.get("create_wa", False)
        result["context"] = {"default_sheet_id": self.id}
        if len(self.wa_ids) > 1 and not create_wa:
            result["domain"] = "[('id', 'in', " + str(self.wa_ids.ids) + ")]"
        else:
            res = self.env.ref(
                "purchase_work_acceptance.view_work_acceptance_form", False
            )
            result["views"] = [(res and res.id or False, "form")]
            if not create_wa:
                result["res_id"] = self.wa_ids.id or False
        return result

    def action_sheet_move_create(self):
        group_required_wa = self.env.user.has_group(
            "hr_expense_work_acceptance.group_wa_accepted_before_inv"
        )
        if group_required_wa and any(not sheet.wa_accepted for sheet in self):
            raise UserError(_("You must have accept WA before Post Journal Entries."))
        return super().action_sheet_move_create()


class HRExpense(models.Model):
    _inherit = "hr.expense"

    wa_line_ids = fields.One2many(
        comodel_name="work.acceptance.line",
        inverse_name="expense_id",
        string="WA Lines",
        readonly=True,
    )
    qty_accepted = fields.Float(
        compute="_compute_qty_accepted",
        string="Accepted Qty.",
        store=True,
        readonly=True,
        digits="Product Unit of Measure",
    )
    qty_to_accept = fields.Float(
        compute="_compute_qty_accepted",
        string="To Accept Qty.",
        store=True,
        readonly=True,
        digits="Product Unit of Measure",
    )

    def _get_product_qty(self):
        return self.quantity - sum(
            wa_line.product_qty
            for wa_line in self.wa_line_ids
            if wa_line.wa_id.state != "cancel"
        )

    @api.depends(
        "wa_line_ids.wa_id.state",
        "wa_line_ids.product_qty",
        "quantity",
        "sheet_id.state",
    )
    def _compute_qty_accepted(self):
        for line in self:
            # compute qty_accepted
            qty = 0.0
            for wa_line in line.wa_line_ids.filtered(
                lambda l: l.wa_id.state == "accept"
            ):
                qty += wa_line.product_uom._compute_quantity(
                    wa_line.product_qty, line.product_uom_id, round=False
                )
            line.qty_accepted = qty

            # compute qty_to_accept
            line.qty_to_accept = line.quantity - line.qty_accepted
