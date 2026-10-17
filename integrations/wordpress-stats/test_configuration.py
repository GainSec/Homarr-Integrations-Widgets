import unittest,tempfile
from server import Connection
from urllib.parse import urlsplit,parse_qs
class ConfigurationTests(unittest.TestCase):
 def test_site_and_callback_are_instance_specific(self):
  with tempfile.TemporaryDirectory() as d:
   c=Connection(d,{'client_id':'123','client_secret':'test'},site_id='987654321',public_base_url='https://dash.example.org',site_label='blog.example.org')
   q=parse_qs(urlsplit(c.begin(c.setup_key)[0]).query)
   self.assertEqual(q['blog'],['987654321']);self.assertEqual(q['redirect_uri'],['https://dash.example.org/wordpress/oauth/callback'])
   self.assertEqual(c.status()['site'],'blog.example.org')
 def test_example_credentials_fail_closed(self):
  from server import validate_secrets
  with self.assertRaises(ValueError):validate_secrets({'proxy_token':'<GENERATE_PROXY_TOKEN>','read_token':'<GENERATE_READ_TOKEN>'},{'client_id':'123','client_secret':'<INSERT_SECRET>'})
