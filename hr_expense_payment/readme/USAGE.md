An expense that has been reimbursed shows a **Payments** button opening the
payments that paid it, for users with accounting access.

The payment shows the mirror **Reimbursed Expenses** button. Core's own
**Expense** button covers company-paid expenses only, and stays hidden on a
reimbursement payment.

Both fields are read-only, searchable, and readable by employees on their
own expenses; use them in views, filters, automations or dependent modules.

Upgrading from 18.0: links the accounting data cannot rebuild are carried
onto the expenses' journal entries by `migrations/19.0.1.0.0/post-migration.py`.
