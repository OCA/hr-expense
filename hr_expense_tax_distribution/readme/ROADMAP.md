- **Analytic distribution per line** — the current implementation copies
  the `analytic_distribution` from the parent expense to every
  distribution line. A future improvement could allow setting a distinct
  analytic distribution on each tax distribution line.
- **Automatic total update** — when the user adjusts the distribution
  lines, the expense *Total* field is not automatically recalculated.
  The user must ensure consistency manually. A future improvement could
  offer a *Recompute Total* helper button.
- **Import / OCR integration** — receipts parsed by the Odoo AI/OCR
  feature do not currently populate distribution lines. Integration with
  the attachment extraction pipeline is a possible future improvement.
