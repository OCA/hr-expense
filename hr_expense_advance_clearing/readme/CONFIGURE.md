This module will create a new product "Employee Advance" automatically.
You will need to setup the Expense Account of this product to your
Employee Advance account manually.

- Open Product window and search for "Employee Advance"
- On Accounting tab, select appropriate employee advance account from
  your chart of account

Note:

- You will need the "Show Full Accounting Features" to see accounting
  data
- Employee Advance account code, if not already exists, you can create
  one. Use type = Current Asset and check Allow Reconciliation.

**Clearing Journal**

Clearing entries are posted as journal entries (move_type 'entry'), which
only allow Miscellaneous (general) journals. By default Odoo picks the
first general journal it finds. To control it:

1.  Go to Settings \> Expenses \> Accounting.
2.  Set the "Default Clearing Journal" to the Miscellaneous journal that
    should receive the clearing entries.

The clearing journal can also be set per clearing report on the report's
"Clearing Journal" field, which defaults to the company setting above.

