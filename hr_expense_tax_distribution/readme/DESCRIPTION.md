In standard Odoo, an expense record accepts a **single set of taxes**
applied to the full total amount. This works well when a receipt is
entirely subject to one VAT rate, but breaks down for mixed receipts
where different line items are taxed at different rates.

A typical example in France is a **restaurant bill**, where the
applicable VAT rates depend on what was consumed:

- **5.5 %** on food (solid items)
- **10 %** on non-alcoholic beverages
- **20 %** on alcoholic beverages

With the standard module, the user is forced to pick a single tax for
the whole amount, which leads to an incorrect tax breakdown in the final
accounting entry and, consequently, to wrong VAT reporting figures.

This module solves the problem by introducing **tax distribution lines**
on the `hr.expense` form. When an expense carries more than one tax, the
user can split the total receipt amount across as many distribution
lines as needed — one per applicable tax rate. Each line holds:

- the **tax** that applies to that portion of the receipt,
- the **base amount (tax excluded)** entered by the user,
- the **tax amount** and the **total (tax included)** computed
  automatically.

A validation constraint ensures that the sum of the distribution line
totals equals the expense total before the expense report can be
submitted.

When the expense report is posted, the accounting entry is built from
the distribution lines instead of the single `tax_ids` / total pair,
producing a correct and auditable VAT breakdown for each applicable
rate.

The module is fully **backward compatible**: expenses with a single tax
or no distribution lines behave exactly as in standard Odoo.
