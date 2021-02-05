# Copyright 2019 Kitti U. <kittiu@ecosoft.co.th>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import models


class HrExpenseSheetRegisterPaymentWizard(models.TransientModel):
    _inherit = "hr.expense.sheet.register.payment.wizard"

    def expense_post_payment(self):
        return super(
            HrExpenseSheetRegisterPaymentWizard,
            self.with_context(use_hr_expense_invoice=True),
        ).expense_post_payment()
