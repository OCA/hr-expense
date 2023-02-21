To use this module, you can do 2 ways:

Cancel all related operations
================================

For delete all document related with expense (payment, journal entries) on the system

#. Go to *Expenses -> My Expenses -> My Expenses to Report* and create a new
   *Expense* with *Employee (to reimburse)* checked on the field *Paid By*
#. Click on *Submit to Manager* button
#. Click on *Approve* button
#. Click on *Post Journal Entries* button
#. Click on *Register Payment* button, fill in the data of the wizard and
   click on *Create Payment* button
#. After that, the *Expense report* will have an associated journal entry
   reconciled with a payment
#. Click on *Cancel all related operations* button
#. The *Expense report* will be set to *Submitted* state; the journal entry and
   the payment will be deleted


Cancel expense for backward state
===================================

For cancel expense/payment and journal entries that related expense.
it will backward state expense following your config

#. Go to *Expenses > Configuration > Settings*
#. Set the policy in "Expense Cancellation Policy"

Case 1: Cancel Expense

#. Go to expenses and normal process until posted
#. Click on *Cancel*, the expense report will be set state following your config in expense cancellation policy (Cancel expense, Expense change state to)

Case 2: Cancel Journal Entries

#. Go to expenses and normal process until posted
#. Go to journal entry that depend on expense > Reset to Draft > Cancel Entry
#. The expense report will be set state following your config in expense cancellation policy (Cancel JE, Expense change state to)

Case 3: Cancel Payment

#. Go to expenses and normal process until Done
#. Go to payment that depend on expense > Reset to Draft > Cancel Entry
#. The expense report will be set state following your config in expense cancellation policy (Cancel payment, Expense change state to)
