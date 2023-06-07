from odoo import SUPERUSER_ID, api


def pre_init_hook(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    module = "sales_team"
    model_data = env["ir.model.data"]
    for i in range(8):
        xml_id = module + ".categ_oppor%s" % str(i + 1)
        record = model_data.xmlid_to_object(xml_id, raise_if_not_found=False)
        if record:
            record.unlink()
