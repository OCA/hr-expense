# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrExpenseSheetRegisterPaymentWizard(models.TransientModel):
    _inherit = "hr.expense.sheet.register.payment.wizard"

    @api.model
    def default_get(self, fields):
        result = super(HrExpenseSheetRegisterPaymentWizard, self).default_get(fields)
        active_id = self._context.get("active_id")
        expense_sheet = self.env["hr.expense.sheet"].browse(active_id)
        if expense_sheet.vendor_id:
            result["partner_id"] = expense_sheet.vendor_id.id
        return result
