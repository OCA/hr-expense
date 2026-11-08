# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrExpensePostWizard(models.TransientModel):
    _inherit = "hr.expense.post.wizard"

    def _ensure_purchase_journal(self):
        """Return a purchase journal for this receipt.

        ``action_post_entry`` copies ``employee_journal_id`` onto the move.
        An empty value is stored as NULL and skips the move's own journal
        default, so the insert fails the NOT NULL constraint.
        """
        self.ensure_one()
        journal = self.sudo().employee_journal_id
        if journal.type == "purchase":
            return journal
        expenses = self.env["hr.expense"].sudo().browse(
            self.env.context.get("active_ids")
        )
        company = expenses.company_id[:1] or self.company_id or self.env.company
        journals = self.env["account.journal"].sudo().with_context(active_test=False)
        journal = journals.search(
            [
                ("company_id", "=", company.id),
                ("type", "=", "purchase"),
            ],
            limit=1,
        )
        if journal and not journal.active:
            journal.active = True
        if not journal:
            journal = journals.create(
                {
                    "name": "Purchases",
                    "code": f"H{company.id:04d}"[:5],
                    "type": "purchase",
                    "company_id": company.id,
                }
            )
        self.sudo().write(
            {
                "company_id": company.id,
                "employee_journal_id": journal.id,
            }
        )
        return journal

    def action_post_entry(self):
        for wizard in self:
            wizard._ensure_purchase_journal()
        return super().action_post_entry()
