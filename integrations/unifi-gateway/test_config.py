import unittest
from unifi_metadata import UniFiClient
class ConfigTests(unittest.TestCase):
 def test_configurable_site(self):
  c=UniFiClient(credentials="credentials.json",origin="https://app.example.net",site="branch")
  self.assertEqual(c.paths["health"],"/proxy/network/api/s/branch/stat/health")
 def test_rejects_path_in_site(self):
  with self.assertRaises(ValueError):UniFiClient(site="../default")
