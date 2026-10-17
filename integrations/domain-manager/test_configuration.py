import unittest
from engine import DNS,Caddy
from server import App
class ConfigurationTests(unittest.TestCase):
 def test_adapters_take_explicit_settings(self):
  self.assertEqual(DNS('http://dns.example.org','test',proxy_address='192.0.2.50').proxy_address,'192.0.2.50')
  self.assertEqual(Caddy(container='edge').container,'edge')
 def test_host_allowlist_is_configurable(self):
  a=App({'proxy_token':'test','allowed_hosts':['dash.example.org'],'allowed_origins':['https://dash.example.org']},None)
  self.assertEqual(a.dispatch('GET','/',{'Host':'dash.example.org','X-Domain-Proxy':'test'},None)[0],200)
  self.assertEqual(a.dispatch('GET','/',{'Host':'example.net','X-Domain-Proxy':'test'},None)[0],403)
 def test_example_credentials_fail_closed(self):
  from server import validate_secrets
  with self.assertRaises(ValueError):validate_secrets({'proxy_token':'<GENERATE_PROXY_TOKEN>','dns_token':'<INSERT_TOKEN>'})
