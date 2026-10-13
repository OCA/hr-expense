**Typical workflow — restaurant receipt (France)**

Consider a receipt for 86.75 € (tax included) with three different VAT
rates:

| Item                    | Base (HT) | Rate  | Tax      | Total (TTC) |
|-------------------------|-----------|-------|----------|-------------|
| Food                    | 50.00 EUR | 5.5 % | 2.75 EUR | 52.75 EUR   |
| Non-alcoholic beverages | 20.00 EUR | 10 %  | 2.00 EUR | 22.00 EUR   |
| Alcoholic beverages     | 10.00 EUR | 20 %  | 2.00 EUR | 12.00 EUR   |
| **Total**               | 80.00 EUR |       | 6.75 EUR | 86.75 EUR   |

**Step-by-step**

1.  Go to **Expenses \> My Expenses** and create a new expense (or open
    an existing draft one).

2.  Fill in the standard fields: *Product*, *Total* (`86.75`),
    *Employee*, *Date*, etc.

3.  In the **Taxes** field, add **all** the VAT rates that appear on the
    receipt (e.g. *TVA 5.5%*, *TVA 10%*, *TVA 20%*).

    As soon as more than one tax is present, the **Tax Distribution**
    table appears automatically below the *Taxes* field, with one
    pre-created line per tax.

4.  For each line in the *Tax Distribution* table, enter the **Base
    Amount (Tax Excl.)** — the portion of the receipt that is subject to
    that particular rate.

    The *Tax Amount* and *Total (Tax Incl.)* columns are computed and
    updated instantly.

5.  Verify that the sum of the *Total (Tax Incl.)* column equals the
    expense *Total* field. Odoo will block submission if there is a
    discrepancy.

6.  Submit and approve the expense report as usual.

**Result in the accounting entry**

Instead of a single expense line with a blended tax, the generated
journal entry contains **one base line and one tax line per distribution
entry**, providing an accurate and auditable VAT breakdown that feeds
correctly into the tax declaration (e.g. French CA3 return).

**Single-tax expenses**

If the expense has only one tax in the *Taxes* field, the *Tax
Distribution* table is not shown and the standard Odoo behaviour applies
unchanged. You can still manually add a distribution line if needed (for
instance, to split a single-rate receipt across two accounts), but this
is an edge case.

**Manual adjustments**

Distribution lines can be added, removed, or edited manually at any time
while the expense is in draft or submitted state (subject to the usual
edit permissions). Use the *handle* icon to reorder them.
