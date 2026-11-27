# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import logging

from odoo.tools.translate import code_translations

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """The trip code used to default to "New" (translated in the user's
    language) when no sequence number could be assigned. The code is optional
    now, so reset these placeholders to an empty code."""
    if not version:
        return
    cr.execute("SELECT code FROM res_lang WHERE active")
    placeholders = {"New"}
    for (lang,) in cr.fetchall():
        translations = code_translations.get_python_translations(
            "hr_expense_trip", lang
        )
        placeholders.add(translations.get("New") or "New")
    cr.execute(
        "UPDATE hr_trip SET code = NULL WHERE code IN %s",
        (tuple(placeholders),),
    )
    _logger.info("Reset the placeholder code of %s trips", cr.rowcount)
