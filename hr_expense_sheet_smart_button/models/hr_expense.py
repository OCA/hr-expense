# Copyright (C) 2022 PT Solusi Aglis Indonesia
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models
from odoo import api

class HrExpenseSheet(models.Model):
    _inherit = "hr.expense.sheet"

    expense_number = fields.Integer('Number of Expenses', compute='_compute_expense_number')

    @api.depends('expense_line_ids')
    def _compute_expense_number(self):
        read_group_result = self.env['hr.expense'].read_group([('sheet_id', 'in', self.ids)], ['sheet_id'], ['sheet_id'])
        result = dict((data['sheet_id'][0], data['sheet_id_count']) for data in read_group_result)
        for sheet in self:
            sheet.expense_number = result.get(sheet.id, 0)

    def action_get_expense_view(self):
        self.ensure_one()
        return {
            'name': ('Expenses'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'hr.expense',
            'domain': [('id', 'in', self.expense_line_ids.ids)],
        }
