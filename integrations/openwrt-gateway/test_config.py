import unittest
from openwrt_metadata import OpenWrtClient
class ConfigTests(unittest.TestCase):
 def test_configurable_host(self):
  c=OpenWrtClient(root="/etc/router",host="router.example.net")
  self.assertEqual(c.command()[-2:], ["root@router.example.net","snapshot"])
 def test_rejects_ssh_options_as_host(self):
  with self.assertRaises(ValueError):OpenWrtClient(host="-oProxyCommand=example")
