To configure this module, you need to:

1.  Enable the “Analytic Accounting” permission on the user
2.  Go to an employee (or create a new one) and set a work address.
    The lookup falls back to the employee's work contact partner
    (`work_contact_id`) when no work address is set.
3.  Go to *Invoicing \> Configuration \> Analytic Accounting \>
    Analytic Distribution Models* and create a record that has as partner
    the employee's work address (or work contact, depending on which is set).
