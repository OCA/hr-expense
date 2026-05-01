No specific configuration is required after installation.

The *Tax Distribution* table is displayed automatically on the expense
form whenever distribution lines exist on the record. Distribution lines
are generated automatically when more than one tax is added to the
*Taxes* field (via the `tax_ids` onchange), but they can also be created
or modified manually.

**Purchase taxes**

Only taxes with *Tax Scope* set to `Purchase` or `All` are available in
the distribution line *Tax* field. Make sure your VAT rates are
configured accordingly (Accounting \> Configuration \> Taxes).

**Company currency**

All amounts in the distribution lines are expressed in the **expense
currency** (`currency_id`), consistent with the standard *Total* field
on the expense. Multi-currency conversion is handled by the existing
Odoo expense mechanism and is not affected by this module.
