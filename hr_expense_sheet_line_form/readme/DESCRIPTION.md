Currently, when users create an expense report first and then add expense
lines, Odoo opens a selection dialog (many2many widget) that is mainly
designed to select existing expenses before creating new ones.

This behavior can be confusing for users who expect a workflow similar to
other Odoo business documents, where lines are created directly from the
parent document.

With this module, expense lines can be added directly from the expense
report using a one2many list view. Users can also open each expense line
in a dedicated form view for detailed editing.
