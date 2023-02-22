To use this module, you must configure product "Employee Advance" with account type = Current Asset and check Allow Reconciliation.
After that, you can step following:

**Create an Employee Advance**

#. Go to Expenses > My Expenses > Advances
#. Create sheet and add a line with advance
#. As an option, the user can also set the "Clearing Product". If this is set, on the clear advance step, the clearing product will create a default product line.
#. Set the unit price to advance amount > Save
#. As normal, do Submit to Manager > Approve > Post Journal Entries > Register Payment.
#. As this is Advance, you will see a new field "Amount to clear".

**Clear Advance**

you can do 2 ways,

#. Create clearing from advance document
    #. Go to Expenses > My Expenses > Advances
    #. Search for the Advance you want to clear, or use filter "Advance (not cleared)" to see all uncleared advance.
    #. Open an Advance which is now in paid status with some Amount to be cleared.
    #. Click button "Clear Advance", system will create new Expense Report with reference to the previous step Advance.
    #. Create name clearing and Save (must save first)
    #. Edit > Add or create Expense line(s) as normal.
    #. As normal, do Approve > Post Journal Entries
#. Create clearing from new expense
    #. Go to Expenses > My Expenses > Expenses
    #. Create sheet and reference advance with field "Clear Advance" > Save (must save first)
    #. Edit > Add or create Expense line(s) as normal.
    #. As normal, do Approve > Post Journal Entries

Note:

* If the total expense amount less than or equal to the advance amount, the status will be set to Paid right after post journal entries.
* If the total expense amount more than the advance amount, Register Payment will pay the extra amount then set state to Paid.

**Return Advance**

#. Go to Expenses > My Expenses > Advances
#. Search for the Advance you want to clear, or use filter "Advance (not cleared)" to see all uncleared advance.
#. Open an Advance which is now in paid status with some Amount to be cleared.
#. Click button "Return Advance" will open Register Payment wizard with Amount to clear.
#. Click button "Create Payment" to return that amount back
#. All returned, Amount to clear is now equal to 0.0
