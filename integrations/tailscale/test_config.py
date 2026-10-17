import unittest
from tailscale_collector import Collector
class ConfigTests(unittest.TestCase):
 def test_configurable_binary(self):
  self.assertEqual(Collector(binary="/opt/bin/tailscale").binary,"/opt/bin/tailscale")
