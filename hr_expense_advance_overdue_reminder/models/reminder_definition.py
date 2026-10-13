# Copyright 2023 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ReminderDefinition(models.Model):
    _name = "reminder.definition"
    _inherit = "base.reminder.mixin"
    _description = "Reminder Definition"

    name = fields.Char(
        string="Description",
        required=True,
    )
    clearing_terms_days = fields.Integer(
        string="Clearing Terms",
        default=30,
        help="In case this field is configured, "
        "the system will help calculate Clearing Date Due according to the term.",
    )
    reminder_number = fields.Integer(string="Reminder Every", default=5)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.company,
    )
