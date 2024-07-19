To use this module, you must configure product "Employee Advance" with
account type = Current Asset and check Allow Reconciliation. After that,
you can step following:

**Create an Employee Advance**

1.  Go to Expenses \> My Expenses \> Advances
2.  Create sheet and add a line with advance
3.  As an option, the user can also set the "Clearing Product". If this
    is set, on the clear advance step, the clearing product will create
    a default product line.
4.  Set the unit price to advance amount \> Save
5.  As normal, do Submit to Manager \> Approve \> Post Journal Entries
    \> Register Payment.
6.  As this is Advance, you will see a new field "Amount to clear".

**Clear Advance**

you can do 2 ways,

1.  Create clearing from advance document  
    1.  Go to Expenses \> My Expenses \> Advances
    2.  Search for the Advance you want to clear, or use filter "Advance
        (not cleared)" to see all uncleared advance.
    3.  Open an Advance which is now in paid status with some Amount to
        be cleared.
    4.  Click button "Clear Advance", system will create new Expense
        Report with reference to the previous step Advance.
    5.  Create name clearing and Save (must save first)
    6.  Edit \> Add or create Expense line(s) as normal.
    7.  As normal, do Approve \> Post Journal Entries

2.  Create clearing from new expense  
    1.  Go to Expenses \> My Expenses \> Expenses
    2.  Create sheet and reference advance with field "Clear Advance" \>
        Save (must save first)
    3.  Edit \> Add or create Expense line(s) as normal.
    4.  As normal, do Approve \> Post Journal Entries

Note:

- If the total expense amount less than or equal to the advance amount,
  the status will be set to Paid right after post journal entries.
- If the total expense amount more than the advance amount, Register
  Payment will pay the extra amount then set state to Paid.

**Return Advance**

1.  Go to Expenses \> My Expenses \> Advances
2.  Search for the Advance you want to clear, or use filter "Advance
    (not cleared)" to see all uncleared advance.
3.  Open an Advance which is now in paid status with some Amount to be
    cleared.
4.  Click button "Return Advance" will open Register Payment wizard with
    Amount to clear.
5.  Click button "Create Payment" to return that amount back
6.  All returned, Amount to clear is now equal to 0.0
