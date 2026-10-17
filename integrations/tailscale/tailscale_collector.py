"""Read-only, authenticated device display metadata from the local daemon.

Bind to the Homarr Docker bridge, not a public/LAN interface. No daemon state,
authentication keys, users, peer keys, routes or API actions are exposed.
"""
import datetime
import hmac
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def authorized(header, token):
    return bool(header and token and hmac.compare_digest(
        header.encode('utf-8'), ('Bearer ' + token).encode('utf-8'),
    ))


def normalize_status(raw):
    state = raw.get('BackendState', 'Unknown')
    if state != 'Running':
        raise RuntimeError('Tailscale collector: ' + str(state))
    if (raw.get('Self') or {}).get('Online') is False:
        raise RuntimeError('Tailscale collector is offline; peer status is unavailable')
    devices = []
    entries = [(raw.get('Self') or {}, True)]
    entries.extend((value, False) for value in (raw.get('Peer') or {}).values())
    for node, is_self in entries:
        if not node:
            continue
        last_seen = node.get('LastSeen')
        if not isinstance(last_seen, str) or last_seen.startswith('0001-'):
            last_seen = None
        online = node.get('Online')
        devices.append({
            'id': str(node.get('ID') or node.get('HostName') or 'unknown')[:200],
            'name': str(node.get('HostName') or node.get('DNSName') or 'Unnamed device')[:200],
            'os': str(node.get('OS') or 'unknown')[:40],
            'online': online if isinstance(online, bool) else None,
            'lastSeen': last_seen,
            'isSelf': is_self,
        })
    return {
        'state': state,
        'scope': 'Devices visible to collector host',
        'collectedAt': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'devices': devices,
    }


class Collector:
    def __init__(self, binary="/usr/bin/tailscale"):
        self.binary = binary
        self.lock = threading.Lock()
        self.expires = 0
        self.cached = None

    def read(self):
        with self.lock:
            if self.cached is not None and time.monotonic() < self.expires:
                return self.cached
            result = subprocess.run(
                [self.binary, 'status', '--json'],
                capture_output=True, text=True, timeout=10, check=True,
            )
            self.cached = normalize_status(json.loads(result.stdout))
            self.expires = time.monotonic() + 30
            return self.cached
