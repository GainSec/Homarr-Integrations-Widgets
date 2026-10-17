import importlib.util
import json
import pathlib
import unittest


class TailscaleStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = pathlib.Path(__file__).with_name('tailscale_collector.py')
        if path.exists():
            spec = importlib.util.spec_from_file_location('collector', path)
            cls.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.module)
        else:
            cls.module = None

    def test_exports_only_display_metadata_and_distinguishes_unknown(self):
        self.assertIsNotNone(self.module, 'Tailscale collector is not implemented')
        payload = self.module.normalize_status({
            'BackendState': 'Running',
            'Self': {'ID': 'local', 'HostName': 'collector', 'Online': True, 'PublicKey': 'SECRET'},
            'Peer': {
                'a': {'ID': 'one', 'HostName': 'online', 'Online': True, 'UserID': 123, 'PublicKey': 'SECRET'},
                'b': {'ID': 'two', 'HostName': 'offline', 'Online': False, 'LastSeen': '2026-10-15T12:00:00Z'},
                'c': {'ID': 'three', 'HostName': 'unknown', 'LastSeen': '0001-01-01T00:00:00Z'},
            },
        })
        by_name = {d['name']: d for d in payload['devices']}
        self.assertIs(by_name['online']['online'], True)
        self.assertIs(by_name['offline']['online'], False)
        self.assertIsNone(by_name['unknown']['online'])
        self.assertIsNone(by_name['unknown']['lastSeen'])
        self.assertTrue(by_name['collector']['isSelf'])
        self.assertNotIn('SECRET', json.dumps(payload))
        self.assertNotIn('UserID', json.dumps(payload))

    def test_disconnected_collector_does_not_publish_offline_devices(self):
        self.assertIsNotNone(self.module, 'Tailscale collector is not implemented')
        with self.assertRaisesRegex(RuntimeError, 'NeedsLogin'):
            self.module.normalize_status({'BackendState': 'NeedsLogin', 'Peer': {'x': {'Online': False}}})

    def test_bearer_auth_is_required(self):
        self.assertIsNotNone(self.module, 'Tailscale collector is not implemented')
        self.assertFalse(self.module.authorized(None, 'key'))
        self.assertFalse(self.module.authorized('Bearer wrong', 'key'))
        self.assertFalse(self.module.authorized('key', 'key'))
        self.assertFalse(self.module.authorized('Bearer \u00a9', 'key'))
        self.assertTrue(self.module.authorized('Bearer key', 'key'))

    def test_running_daemon_with_disconnected_self_is_unavailable(self):
        self.assertIsNotNone(self.module, 'Tailscale collector is not implemented')
        with self.assertRaisesRegex(RuntimeError, 'offline'):
            self.module.normalize_status({
                'BackendState': 'Running',
                'Self': {'ID': 'local', 'Online': False},
                'Peer': {'a': {'ID': 'peer', 'Online': True}},
            })


if __name__ == '__main__':
    unittest.main()
