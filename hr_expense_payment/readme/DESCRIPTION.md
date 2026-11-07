This module links each employee-paid expense to the payment(s) that settled
it, in both directions: `hr.expense.payment_ids` and
`account.payment.reconciled_expense_ids`.

Both fields are computed from core's move-level link data — reconciled
payments, partials included, and payments matched by the payment register —
so nothing is stored that could go stale. Core's own
`account.payment.expense_ids` covers company-paid expenses; these fields
cover the employee-reimbursement direction.
