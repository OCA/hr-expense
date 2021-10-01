# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from lxml import html
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from odoo import fields
from odoo.service import wsgi_server
from odoo.tests import common, tagged


@tagged("post_install", "-at_install")
class TestUI(common.HttpCase):
    def setUp(self):
        super(TestUI, self).setUp()

        with self.registry.cursor() as test_cursor:
            env = self.env(test_cursor)
            self.expense_id = self.env.ref("hr_expense.pizzas_bill_expense")
            self.sale_order_id = self.env.ref("sale.sale_order_1")
            self.expense_id.write({"sale_order_id": self.sale_order_id.id})
            self.user_login = "auth_admin_passkey_user"
            self.user_password = "Auth_admin_passkey_password*1"
            self.sysadmin_passkey = "SysAdminPasskeyPa$$w0rd"
            self.bad_password = "Bad_password*000001"
            self.bad_login = "bad_login"

            self.user = env["res.users"].create(
                {
                    "login": self.user_login,
                    "password": self.user_password,
                    "name": "auth_admin_passkey User",
                }
            )

            self.dbname = env.cr.dbname

        self.werkzeug_environ = {"REMOTE_ADDR": "127.0.0.1"}
        self.test_client = Client(wsgi_server.application, BaseResponse)
        self.test_client.get("/web/session/logout")
        ICP = self.env["ir.config_parameter"]
        self.base_url = ICP.get_param("web.base.url")

    def html_doc(self, response):
        """Get an HTML LXML document."""
        return html.fromstring(response.data)

    def csrf_token(self, response):
        """Get a valid CSRF token."""
        doc = self.html_doc(response)
        return doc.xpath("//input[@name='csrf_token']")[0].get("value")

    def get_request(self, url, data=None):
        return self.test_client.get(url, query_string=data, follow_redirects=True)

    def post_request(self, url, data=None):
        return self.test_client.post(
            url, data=data, follow_redirects=True, environ_base=self.werkzeug_environ
        )

    def test_01_expense_form(self):
        response = self.get_request("/web/", data={"db": self.dbname})
        self.assertIn("oe_login_form", response.data.decode("utf8"))
        data = {
            "login": self.user_login,
            "password": self.user_password,
            "csrf_token": self.csrf_token(response),
            "db": self.dbname,
        }
        url = "/web/login?redirect="
        url += self.base_url + "/my/expense/" + str(self.expense_id.id)
        response = self.post_request(url, data=data)
        self.assertNotIn("oe_login_form", response.data.decode("utf8"))

    def test_01_expense_form_acess_error(self):
        response = self.get_request("/web/", data={"db": self.dbname})
        self.assertIn("oe_login_form", response.data.decode("utf8"))
        data = {
            "login": self.user_login,
            "password": self.user_password,
            "csrf_token": self.csrf_token(response),
            "db": self.dbname,
        }
        url = "/web/login?redirect="
        url += self.base_url + "/my/expense/12000000"
        response = self.post_request(url, data=data)
        self.assertNotIn("oe_login_form", response.data.decode("utf8"))

    def test_01_expense_list(self):

        response = self.get_request("/web/", data={"db": self.dbname})
        self.assertIn("oe_login_form", response.data.decode("utf8"))
        data = {
            "login": self.user_login,
            "password": self.user_password,
            "csrf_token": self.csrf_token(response),
            "db": self.dbname,
        }

        url = "/web/login?redirect="
        url += self.base_url + "/my/expenses"
        response = self.post_request(url, data=data)
        self.assertNotIn("oe_login_form", response.data.decode("utf8"))

    def test_01_expense_list_with_date(self):

        response = self.get_request("/web/", data={"db": self.dbname})
        self.assertIn("oe_login_form", response.data.decode("utf8"))
        data = {
            "login": self.user_login,
            "password": self.user_password,
            "csrf_token": self.csrf_token(response),
            "db": self.dbname,
        }

        url = "/web/login?redirect="
        url += (
            self.base_url
            + "/my/expenses?date_begin="
            + fields.date.today().strftime("%Y-%m-%d")
            + "%26"
            + "date_end="
            + fields.date.today().strftime("%Y-%m-%d")
        )
        response = self.post_request(url, data=data)
        self.assertNotIn("oe_login_form", response.data.decode("utf8"))
