import unittest
from unifi_metadata import sanitize, UniFiClient

class UniFiTests(unittest.TestCase):
    def test_allowlist_excludes_secrets_and_unneeded_fields(self):
        d=sanitize({'meta':{'rc':'ok'},'data':[{'name':'a','mac':'00:00','password':'secret','fingerprint':{'raw':'secret'},'rx_bytes-r':12}]},'clients')
        self.assertEqual(d['data'],[{'name':'a','mac':'00:00','rx_bytes-r':12}])
        h=sanitize({'meta':{'rc':'ok'},'data':[{'subsystem':'wan','gw_system-stats':{'cpu':'10','mem':'20','token':'secret'},'uptime_stats':{'WAN':{'availability':100,'token':'secret'}}}]},'health')
        self.assertNotIn('secret',str(h))
    def test_only_fixed_read_endpoints(self):
        client=UniFiClient('/nonexistent')
        with self.assertRaises(ValueError):client.read('speedtest')
        with self.assertRaises(ValueError):sanitize({'meta':{'rc':'error'},'data':[]},'health')
        self.assertEqual(set(client.paths),{'health','clients'})

if __name__=='__main__':unittest.main()
