# Copyright 2021 Ecosoft
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class RequestChildDoc(models.Model):
    _inherit = "request.child.doc"

    def _update_doc_info(self):
        super()._update_doc_info()
        if self.res_model == "hr.expense.sheet":
            self.update(
                {
                    "doc_amount": self.doc_ref.total_amount,
                    "doc_note": self.doc_ref.name,
                    "doc_status": dict(self.doc_ref._fields["state"].selection).get(
                        self.doc_ref.state
                    ),
                }
            )

    def _get_sql(self):
        queries = super()._get_sql()
        queries.append(
            """
            select
                2000000 + ex.id as id,
                ref_request_id as request_id,
                ex.id as res_id,
                'hr.expense.sheet' as res_model,
                'hr.expense.sheet,' || ex.id as doc_ref
            from hr_expense_sheet ex
            where ex.ref_request_id is not null
        """
        )
        return queries
