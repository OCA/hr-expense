1. Go to *Expenses > My Trips* and create a new trip.
2. Fill in the trip name, dates, employee, and optional partner/reason.
3. Click *Request Approval*:
   In this step, pre-trip approvals can be handled, and additional workflows
   can be triggered after approval (for example an A1 certificate process).
   - If **Auto Approve Trip Requests** is enabled, the trip moves directly to
     *Collect Receipts*.
   - Otherwise, if the requester is already an allowed approver for that trip,
     it is approved immediately without creating an activity.
   - Otherwise, a *Trip Approval Request* activity is created for the manager.
4. In the *Expenses* tab, use *Add* to select existing draft expenses for the
   same employee, then save.
5. Click an expense line to open the *hr.expense* form when you need to review
   or edit that expense.
6. When all expenses are complete, click *Mark as Done* to finalize the trip
   and attach the generated trip report in chatter.
7. To create bills from approved expenses, click *Create Bill* (visible only
   when trip is in state done all expenses are in approved state). This will 
   post all expenses and attach the trip PDF to each resulting bill.


Role behavior
-------------

- Employees can create and edit their own trips.
- Managers/approvers can view and approve trips they are responsible for.
- Expense administrators can edit all trips.
- After a trip is approved, only managers/administrators can edit trip
  information.
- The *Expenses* tab remains editable until the trip reaches *Done*.

Manager processing menu
-----------------------

Managers can open *Expenses > Trip to Process* to review requested trips where
they are responsible as manager.

Create Bill feature
-------------------

The *Create Bill* button is automatically displayed when all expenses linked to
the trip are in approved state and the trip is in state done. Clicking this button will:

1. Post all approved expenses and create bills.
2. Automatically attach the trip PDF report to each created bill in the chatter.
3. Navigate to the created bill(s) for review.

This streamlines the billing process by ensuring the trip documentation is
automatically associated with the financial records.

Configuration
-------------

To configure auto approval, go to *Expenses > Configuration > Settings* and in
the *Trips* section enable or disable *Auto Approve Trip Requests*.
