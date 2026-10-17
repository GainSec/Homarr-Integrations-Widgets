"""Bounded read-only UniFi display feed using the existing view-only account."""
import http.cookiejar
import json
import pathlib
import re
from configure_widget import checked_url
import threading
import time
import urllib.error
import urllib.request

CLIENT_FIELDS = ('name','hostname','ip','mac','is_wired','signal','essid','radio','sw_port','dev_id','dev_id_override','rx_bytes-r','tx_bytes-r')
HEALTH_FIELDS = ('subsystem','status','isp_name','rx_bytes-r','tx_bytes-r','speedtest_lastrun','xput_down','xput_up','speedtest_ping')


def sanitize(payload, kind):
    if kind not in ('health', 'clients'):
        raise ValueError('Unsupported feed')
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
        raise ValueError('Invalid UniFi response')
    if payload.get('meta', {}).get('rc') != 'ok':
        raise ValueError('UniFi request failed')
    fields = HEALTH_FIELDS if kind == 'health' else CLIENT_FIELDS
    rows=[]
    for raw in payload['data'][:500]:
        if not isinstance(raw, dict):
            continue
        row={k:(v[:256] if isinstance(v,str) else v) for k in fields if isinstance((v:=raw.get(k)),(str,int,float,bool))}
        if kind=='health':
            stats=raw.get('gw_system-stats') or {}
            row['gw_system-stats']={k:stats[k] for k in ('cpu','mem') if isinstance(stats.get(k),(str,int,float))}
            wan=(raw.get('uptime_stats') or {}).get('WAN') or {}
            row['uptime_stats']={'WAN':{k:wan[k] for k in ('latency_average','availability') if isinstance(wan.get(k),(int,float))}}
        rows.append(row)
    return {'meta':{'rc':'ok'},'data':rows}


class UniFiClient:
    origin='https://app.example.net'
    paths={'health':'/proxy/network/api/s/default/stat/health','clients':'/proxy/network/api/s/default/stat/sta'}

    def __init__(self, credentials='/etc/homarr-unifi-gateway/credentials.json', origin='https://app.example.net', site='default'):
        self.origin=checked_url(origin)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',site):raise ValueError('Invalid UniFi site')
        self.paths={k:'/proxy/network/api/s/'+site+'/stat/'+suffix for k,suffix in [('health','health'),('clients','sta')]}
        self.credentials=pathlib.Path(credentials)
        self.opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.lock=threading.RLock()
        self.cache={}
        self.logged_in=False

    def request(self, path, body=None):
        req=urllib.request.Request(self.origin+path, data=json.dumps(body).encode() if body else None, headers={'Content-Type':'application/json'})
        with self.opener.open(req, timeout=12) as response:
            raw=response.read(2*1024*1024+1)
        if len(raw)>2*1024*1024:
            raise RuntimeError('Response too large')
        return json.loads(raw)

    def login(self):
        creds=json.loads(self.credentials.read_text())
        self.request('/api/auth/login', {'username':creds['username'],'password':creds['password'],'rememberMe':True})
        self.logged_in=True

    def read(self, kind):
        if kind not in self.paths:
            raise ValueError('Unsupported feed')
        with self.lock:
            cached=self.cache.get(kind)
            if cached and time.monotonic()<cached[0]:
                return cached[1]
            if not self.logged_in:
                self.login()
            try:
                data=self.request(self.paths[kind])
            except urllib.error.HTTPError as e:
                if e.code!=401:
                    raise
                self.login()
                data=self.request(self.paths[kind])
            result=sanitize(data,kind)
            self.cache[kind]=(time.monotonic()+(15 if kind=='health' else 30),result)
            return result
